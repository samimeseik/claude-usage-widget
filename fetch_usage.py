#!/usr/bin/env python3
"""
Fetch Claude usage data - triple fallback strategy:
  1. curl_cffi with Chrome cookies (fast, no browser needed)
  2. AppleScript via Chrome tab (needs claude.ai tab open)
  3. Return last good cached data (always available)
"""
import sqlite3, shutil, tempfile, json, os, re, subprocess, hashlib, time
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

VERSION = "2.3.0"
REPO = "samimeseik/claude-usage-widget"

COOKIE_DB = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies")
SAFARI_COOKIES = os.path.expanduser("~/Library/Cookies/Cookies.binarycookies")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "usage_history.json")
UPDATE_CHECK_FILE = os.path.join(SCRIPT_DIR, ".last_update_check")
NOTIFIED_FILE = os.path.join(SCRIPT_DIR, ".last_notified")

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

_cfg = load_config()
CACHE = _cfg.get("cache_path", "/tmp/claude_usage_cache.json")

# ─── Widget layout config (position/size/sections) ─────────────────

# Default widget layout. User overrides via config.json["widgets"].
# All sections listed in `show` arrays are enabled by default — the
# user trims them down to what they want.
DEFAULT_USAGE_SECTIONS = [
    "session", "weekly", "sonnet", "extra", "other_accounts", "code_summary"
]
DEFAULT_CODE_SECTIONS = [
    "today", "projects_7d", "heatmap", "hourly", "leaderboard"
]
DEFAULT_WIDGETS = {
    "usage": {
        "enabled": True,
        "anchor": {"vertical": "bottom", "horizontal": "left"},
        "offset": {"x": 24, "y": 24},
        "width": 280,
        "show": list(DEFAULT_USAGE_SECTIONS),
    },
    "code": {
        "enabled": True,
        "anchor": {"vertical": "bottom", "horizontal": "right"},
        "offset": {"x": 24, "y": 24},
        "width": 300,
        "show": list(DEFAULT_CODE_SECTIONS),
    },
}

def _resolve_widget_config():
    """Merge user widget overrides on top of defaults."""
    user = _cfg.get("widgets") or {}
    if not isinstance(user, dict):
        user = {}
    out = {}
    for key in ("usage", "code"):
        merged = json.loads(json.dumps(DEFAULT_WIDGETS[key]))
        u = user.get(key) or {}
        if isinstance(u, dict):
            for k, v in u.items():
                if k in ("anchor", "offset") and isinstance(v, dict):
                    merged[k].update(v)
                else:
                    merged[k] = v
        out[key] = merged
    return out

WIDGET_CONFIG = _resolve_widget_config()

def _accounts_from_config(cfg):
    """Resolve account list from config.

    Supports two schemas:
      - New: {"accounts": [{"org_id": "...", "label": "Main", "primary": true}]}
      - Legacy: {"org_id": "..."} → single unnamed account
    Returns list of {org_id, label, primary} dicts.
    """
    accounts = cfg.get("accounts")
    if isinstance(accounts, list) and accounts:
        out = []
        for i, a in enumerate(accounts):
            oid = a.get("org_id")
            if not oid:
                continue
            out.append({
                "org_id": oid,
                "label": a.get("label") or f"Account {i + 1}",
                "primary": bool(a.get("primary")) if i > 0 else True,
            })
        if out:
            # Make sure exactly one account is primary (first by default)
            if not any(a["primary"] for a in out):
                out[0]["primary"] = True
            return out
    legacy = cfg.get("org_id")
    if legacy:
        return [{"org_id": legacy, "label": "Main", "primary": True}]
    return []

ACCOUNTS = _accounts_from_config(_cfg)
ORG_ID = ACCOUNTS[0]["org_id"] if ACCOUNTS else ""

if not ACCOUNTS:
    print(json.dumps({"error": "Run install.sh first — no accounts in config.json"}))
    raise SystemExit(1)

# ─── Strategy 1: curl_cffi with Chrome cookies ─────────────────────

def get_cookies():
    result = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", "Chrome Safe Storage"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {}
    key = result.stdout.strip()
    dk = hashlib.pbkdf2_hmac('sha1', key.encode('utf-8'), b'saltysalt', 1003, dklen=16)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    shutil.copy2(COOKIE_DB, tmp.name)

    cookies = {}
    try:
        conn = sqlite3.connect(tmp.name)
        cur = conn.cursor()
        cur.execute('SELECT name, encrypted_value FROM cookies WHERE host_key IN (".claude.ai","claude.ai")')
        for name, enc in cur.fetchall():
            if not enc:
                continue
            if enc[:3] == b'v10':
                enc = enc[3:]
            cipher2 = Cipher(algorithms.AES(dk), modes.CBC(b' ' * 16), backend=default_backend())
            dec = cipher2.decryptor()
            d = dec.update(enc) + dec.finalize()
            pad = d[-1]
            if isinstance(pad, int) and 1 <= pad <= 16:
                d = d[:-pad]
            raw = d.decode('latin-1')
            m = re.search(r'(sk-ant-\S+)', raw)
            if m:
                cookies[name] = m.group(1)
                continue
            m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', raw)
            if m:
                cookies[name] = m.group(1)
                continue
            parts = re.findall(r'([!-~]{8,})', raw)
            if parts:
                cookies[name] = max(parts, key=len)
        conn.close()
    finally:
        os.unlink(tmp.name)
    return cookies

def fetch_via_cookies(retries=2, org_id=None):
    """Strategy 1: Direct API call using Chrome cookies + curl_cffi."""
    try:
        from curl_cffi import requests
    except ImportError:
        return None, "curl_cffi not installed"

    cookies = get_cookies()
    if 'sessionKey' not in cookies:
        return None, "no session cookie"

    target = org_id or ORG_ID
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                f"https://claude.ai/api/organizations/{target}/usage",
                cookies=cookies, impersonate="chrome", timeout=20
            )
            if resp.status_code == 200:
                return resp.json(), None
            last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = str(e)[:80]
        if attempt < retries:
            time.sleep(2)
    return None, last_err

# ─── Strategy 2: AppleScript via browser tab (Chrome + Safari) ──────

def _try_browser_tab(browser, app_check, tab_loop, org_id=None):
    """Generic browser tab JS execution."""
    target = org_id or ORG_ID
    js = (
        "(async()=>{"
        "try{"
        f"const r=await fetch('https://claude.ai/api/organizations/{target}/usage',"
        "{credentials:'include'});"
        "if(!r.ok)return JSON.stringify({error:'HTTP '+r.status});"
        "return JSON.stringify(await r.json())"
        "}catch(e){return JSON.stringify({error:e.message})}"
        "})()"
    )
    applescript = f'''
    tell application "System Events"
        if not (exists process "{browser}") then return "{{\\"error\\":\\"{browser} not running\\"}}"
    end tell
    {tab_loop.format(js=js)}
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True, text=True, timeout=12
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if "error" not in data:
                return data, None
            return None, data["error"]
    except subprocess.TimeoutExpired:
        return None, f"{browser} timeout"
    except Exception as e:
        return None, str(e)[:80]
    return None, f"{browser} failed"

def fetch_via_chrome_tab(org_id=None):
    """Strategy 2a: Execute JS in an open claude.ai Chrome tab."""
    tab_loop = '''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t starts with "https://claude.ai" then
                    return (execute t javascript "{js}")
                end if
            end repeat
        end repeat
        return "{{\\"error\\":\\"No Claude tab\\"}}"
    end tell
    '''
    return _try_browser_tab("Google Chrome", "Google Chrome", tab_loop, org_id)

def fetch_via_safari_tab(org_id=None):
    """Strategy 2b: Execute JS in an open claude.ai Safari tab."""
    tab_loop = '''
    tell application "Safari"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t starts with "https://claude.ai" then
                    return (do JavaScript "{js}" in t)
                end if
            end repeat
        end repeat
        return "{{\\"error\\":\\"No Claude tab in Safari\\"}}"
    end tell
    '''
    return _try_browser_tab("Safari", "Safari", tab_loop, org_id)

# ─── Strategy 3: Cache (per-account) ────────────────────────────────

def _account_suffix(account):
    """Short stable suffix per account for per-account state files."""
    if not account:
        return ""
    if account.get("primary"):
        return ""  # Primary = legacy unsuffixed paths (back-compat)
    oid = account.get("org_id", "")
    return "_" + oid.split("-")[0]

def cache_path_for(account):
    suffix = _account_suffix(account)
    if not suffix:
        return CACHE
    base, ext = os.path.splitext(CACHE)
    return f"{base}{suffix}{ext}"

def history_path_for(account):
    suffix = _account_suffix(account)
    if not suffix:
        return HISTORY_FILE
    base, ext = os.path.splitext(HISTORY_FILE)
    return f"{base}{suffix}{ext}"

def load_cache(account=None):
    """Strategy 3: Return last known good data."""
    path = cache_path_for(account) if account else CACHE
    try:
        with open(path, 'r') as f:
            cached = json.load(f)
        if "error" not in cached and cached.get("five_hour"):
            return cached
    except Exception:
        pass
    return None

def save_cache(data, account=None):
    path = cache_path_for(account) if account else CACHE
    data["_ts"] = datetime.now().isoformat()
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# ─── Update check (once per day, non-blocking) ─────────────────────

def check_for_update():
    """Check GitHub for newer version. Runs at most once per day."""
    try:
        # Only check once per day
        if os.path.exists(UPDATE_CHECK_FILE):
            age = time.time() - os.path.getmtime(UPDATE_CHECK_FILE)
            if age < 86400:  # 24 hours
                with open(UPDATE_CHECK_FILE, 'r') as f:
                    return f.read().strip() or None
                return None

        import urllib.request
        url = f"https://api.github.com/repos/{REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "claude-widget"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        latest = data.get("tag_name", "").lstrip("v")

        update_msg = None
        if latest and latest != VERSION:
            update_msg = latest

        with open(UPDATE_CHECK_FILE, 'w') as f:
            f.write(update_msg or "")
        return update_msg
    except Exception:
        # Never let update check break the widget
        try:
            with open(UPDATE_CHECK_FILE, 'w') as f:
                f.write("")
        except Exception:
            pass
        return None

# ─── macOS Notifications ────────────────────────────────────────────

def send_notification(title, message, sound=True):
    """Send a macOS notification via osascript."""
    sound_str = 'sound name "Blow"' if sound else ""
    script = f'display notification "{message}" with title "{title}" {sound_str}'
    try:
        subprocess.run(["osascript", "-e", script], timeout=5,
                       capture_output=True)
    except Exception:
        pass

def check_and_notify(data, account=None):
    """Send notification when usage crosses thresholds (80%, 90%, 100%)."""
    thresholds = [80, 90, 100]
    alerts = []

    for key, label in [("five_hour", "Session"), ("seven_day", "Weekly")]:
        bucket = data.get(key, {})
        pct = bucket.get("utilization", 0)
        for t in thresholds:
            if pct >= t:
                alerts.append((key, t, label, pct))

    if not alerts:
        return

    # Account-scoped notification key prefix avoids cross-account suppression
    acct_prefix = ""
    acct_suffix_msg = ""
    if account:
        acct_prefix = (account.get("org_id", "")[:8] or "main") + "_"
        acct_suffix_msg = f" [{account.get('label')}]" if account.get("label") and not account.get("primary") else ""

    # Load last notified state to avoid spam
    notified = {}
    try:
        with open(NOTIFIED_FILE, 'r') as f:
            notified = json.load(f)
    except Exception:
        pass

    new_alerts = []
    for key, threshold, label, pct in alerts:
        notif_key = f"{acct_prefix}{key}_{threshold}"
        last = notified.get(notif_key, 0)
        # Re-notify only if >30min since last notification for this threshold
        if time.time() - last > 1800:
            new_alerts.append((label, threshold, pct))
            notified[notif_key] = time.time()

    if new_alerts:
        # Group into one notification
        lines = [f"{label}: {pct:.0f}%" for label, _, pct in new_alerts]
        msg = " | ".join(lines) + acct_suffix_msg
        t_max = max(t for _, t, _ in new_alerts)
        if t_max >= 100:
            send_notification("Claude Usage — Limit Reached", msg)
        elif t_max >= 90:
            send_notification("Claude Usage — Almost Full", msg)
        else:
            send_notification("Claude Usage — High Usage", msg)

        try:
            with open(NOTIFIED_FILE, 'w') as f:
                json.dump(notified, f)
        except Exception:
            pass

# ─── Usage History (trends) ─────────────────────────────────────────

def record_history(data, account=None):
    """Record a data point every 30 minutes for trend tracking."""
    path = history_path_for(account) if account else HISTORY_FILE
    history = []
    try:
        with open(path, 'r') as f:
            history = json.load(f)
    except Exception:
        pass

    now = time.time()
    # Only record every 30 minutes
    if history and now - history[-1].get("t", 0) < 1800:
        return

    entry = {
        "t": now,
        "ts": datetime.now().strftime("%H:%M"),
        "s": data.get("five_hour", {}).get("utilization", 0),
        "w": data.get("seven_day", {}).get("utilization", 0),
    }
    sn = data.get("seven_day_sonnet")
    if sn:
        entry["sn"] = sn.get("utilization", 0)

    history.append(entry)
    # Keep last 48 hours (96 entries at 30min interval)
    history = history[-96:]

    try:
        with open(path, 'w') as f:
            json.dump(history, f)
    except Exception:
        pass

def get_trend(data, account=None):
    """Calculate trend arrows by comparing to last recorded value."""
    path = history_path_for(account) if account else HISTORY_FILE
    try:
        with open(path, 'r') as f:
            history = json.load(f)
        if len(history) < 2:
            return {}
        prev = history[-2]
        trends = {}
        for key, hkey in [("five_hour", "s"), ("seven_day", "w")]:
            curr = data.get(key, {}).get("utilization", 0)
            old = prev.get(hkey, 0)
            if curr > old + 2:
                trends[key] = "up"
            elif curr < old - 2:
                trends[key] = "down"
            else:
                trends[key] = "stable"
        return trends
    except Exception:
        return {}

def load_history(account=None):
    path = history_path_for(account) if account else HISTORY_FILE
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def compute_eta(data, history):
    """Calculate ETA when each metric reaches 100% based on recent burn rate.

    Returns ISO timestamps for {five_hour, seven_day} only when:
      - We have at least 30 minutes of data
      - The rate is meaningfully positive (>0.5%/hour)
      - The ETA falls BEFORE the natural reset (otherwise meaningless)
    """
    if len(history) < 3:
        return {}
    recent = history[-6:]  # last ~3 hours of 30-min samples
    eta = {}
    now = time.time()
    for key, hkey in [("five_hour", "s"), ("seven_day", "w")]:
        bucket = data.get(key) or {}
        current = bucket.get("utilization", 0) or 0
        if current >= 100:
            continue
        first = recent[0]
        last = recent[-1]
        time_diff_hours = (last.get("t", 0) - first.get("t", 0)) / 3600
        if time_diff_hours < 0.5:
            continue
        pct_diff = last.get(hkey, 0) - first.get(hkey, 0)
        rate = pct_diff / time_diff_hours
        if rate <= 0.5:
            continue
        hours_to_full = (100 - current) / rate
        eta_t = now + (hours_to_full * 3600)
        # Only show ETA if it occurs before the natural reset
        reset_iso = bucket.get("resets_at")
        if reset_iso:
            try:
                reset_t = datetime.fromisoformat(reset_iso.replace("Z", "+00:00")).timestamp()
                if eta_t >= reset_t:
                    continue
            except Exception:
                pass
        eta[key] = datetime.fromtimestamp(eta_t).isoformat()
    return eta

def get_sparkline(history, n=24):
    """Return last N points for sparkline rendering."""
    spark = {"s": [], "w": [], "sn": []}
    for h in history[-n:]:
        spark["s"].append(round(h.get("s", 0), 1))
        spark["w"].append(round(h.get("w", 0), 1))
        if "sn" in h:
            spark["sn"].append(round(h.get("sn", 0), 1))
    return spark

# ─── Main: try all strategies in order ──────────────────────────────

def get_code_stats():
    """Read Claude Code stats. Best-effort — never breaks the widget."""
    try:
        # Look in same dir or fall back to widget install
        here = SCRIPT_DIR
        cs_path = os.path.join(here, "code_stats.py")
        if not os.path.exists(cs_path):
            return None
        # Import dynamically to keep startup cheap when not installed
        import importlib.util
        spec = importlib.util.spec_from_file_location("code_stats", cs_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.collect_stats()
    except Exception:
        return None

def enrich(data, method, account):
    """Attach trends, ETA, sparkline + cache/history per account."""
    data["_method"] = method
    save_cache(data, account)
    check_and_notify(data, account)
    record_history(data, account)
    history = load_history(account)
    data["_trends"] = get_trend(data, account)
    data["_eta"] = compute_eta(data, history)
    data["_spark"] = get_sparkline(history)
    return data

def fetch_for_account(account):
    """Run the strategy stack for one account. Returns enriched data or None."""
    org_id = account["org_id"]

    # Strategy 1: cookies
    data, err1 = fetch_via_cookies(org_id=org_id)
    if data:
        return enrich(data, "cookies", account), None

    # Strategy 2a: Chrome tab
    data, err2 = fetch_via_chrome_tab(org_id=org_id)
    if data:
        return enrich(data, "chrome_tab", account), None

    # Strategy 2b: Safari tab
    data, err3 = fetch_via_safari_tab(org_id=org_id)
    if data:
        return enrich(data, "safari_tab", account), None

    # Strategy 3: stale cache
    cached = load_cache(account)
    if cached:
        cached["_stale"] = True
        cached["_error"] = f"cookies: {err1} | chrome: {err2} | safari: {err3}"
        history = load_history(account)
        cached["_trends"] = get_trend(cached, account)
        cached["_eta"] = compute_eta(cached, history)
        cached["_spark"] = get_sparkline(history)
        return cached, None

    return None, f"all methods failed: {err1}"

def main():
    primary_data = None
    accounts_out = []
    primary_error = None

    for account in ACCOUNTS:
        data, err = fetch_for_account(account)
        if data is None:
            # Skip dead accounts but record their error
            accounts_out.append({
                "label": account["label"],
                "org_id": account["org_id"],
                "primary": account.get("primary", False),
                "error": err or "unknown",
            })
            if account.get("primary"):
                primary_error = err
            continue

        # Strip out top-level metadata that belongs at the response root
        # (we want it once per account in _accounts, but for primary we also
        # promote the whole payload to the response root for back-compat).
        accounts_out.append({
            "label": account["label"],
            "org_id": account["org_id"],
            "primary": account.get("primary", False),
            "data": data,
        })
        if account.get("primary"):
            primary_data = data

    # Build response: primary account at root + _accounts list
    if primary_data:
        out = dict(primary_data)
        out["_accounts"] = accounts_out
        out["_widgets"] = WIDGET_CONFIG

        # Code stats and update check are global, attach once at root
        code = get_code_stats()
        if code:
            out["_code"] = code
        update = check_for_update()
        if update:
            out["_update"] = update

        print(json.dumps(out))
        return

    # Primary account failed — return error
    out = {
        "error": primary_error or "All methods failed for primary account",
        "_accounts": accounts_out,
        "_widgets": WIDGET_CONFIG,
        "_ts": datetime.now().isoformat(),
    }
    print(json.dumps(out))

if __name__ == "__main__":
    main()
