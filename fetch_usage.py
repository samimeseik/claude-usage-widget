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

VERSION = "1.1.0"
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
ORG_ID = _cfg.get("org_id", "")
CACHE = _cfg.get("cache_path", "/tmp/claude_usage_cache.json")

if not ORG_ID:
    print(json.dumps({"error": "Run install.sh first — no org_id in config.json"}))
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

def fetch_via_cookies(retries=2):
    """Strategy 1: Direct API call using Chrome cookies + curl_cffi."""
    try:
        from curl_cffi import requests
    except ImportError:
        return None, "curl_cffi not installed"

    cookies = get_cookies()
    if 'sessionKey' not in cookies:
        return None, "no session cookie"

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                f"https://claude.ai/api/organizations/{ORG_ID}/usage",
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

def _try_browser_tab(browser, app_check, tab_loop):
    """Generic browser tab JS execution."""
    js = (
        "(async()=>{"
        "try{"
        f"const r=await fetch('https://claude.ai/api/organizations/{ORG_ID}/usage',"
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

def fetch_via_chrome_tab():
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
    return _try_browser_tab("Google Chrome", "Google Chrome", tab_loop)

def fetch_via_safari_tab():
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
    return _try_browser_tab("Safari", "Safari", tab_loop)

# ─── Strategy 3: Cache ──────────────────────────────────────────────

def load_cache():
    """Strategy 3: Return last known good data."""
    try:
        with open(CACHE, 'r') as f:
            cached = json.load(f)
        if "error" not in cached and cached.get("five_hour"):
            return cached
    except Exception:
        pass
    return None

def save_cache(data):
    data["_ts"] = datetime.now().isoformat()
    try:
        with open(CACHE, 'w') as f:
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

def check_and_notify(data):
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

    # Load last notified state to avoid spam
    notified = {}
    try:
        with open(NOTIFIED_FILE, 'r') as f:
            notified = json.load(f)
    except Exception:
        pass

    new_alerts = []
    for key, threshold, label, pct in alerts:
        notif_key = f"{key}_{threshold}"
        last = notified.get(notif_key, 0)
        # Re-notify only if >30min since last notification for this threshold
        if time.time() - last > 1800:
            new_alerts.append((label, threshold, pct))
            notified[notif_key] = time.time()

    if new_alerts:
        # Group into one notification
        lines = [f"{label}: {pct:.0f}%" for label, _, pct in new_alerts]
        msg = " | ".join(lines)
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

def record_history(data):
    """Record a data point every 30 minutes for trend tracking."""
    history = []
    try:
        with open(HISTORY_FILE, 'r') as f:
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
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except Exception:
        pass

def get_trend(data):
    """Calculate trend arrows by comparing to last recorded value."""
    try:
        with open(HISTORY_FILE, 'r') as f:
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

# ─── Main: try all strategies in order ──────────────────────────────

def main():
    # Strategy 1: curl_cffi (fastest, most reliable)
    data, err1 = fetch_via_cookies()
    if data:
        data["_method"] = "cookies"
        save_cache(data)
        check_and_notify(data)
        record_history(data)
        data["_trends"] = get_trend(data)
        update = check_for_update()
        if update:
            data["_update"] = update
        print(json.dumps(data))
        return

    # Strategy 2a: AppleScript Chrome tab
    data, err2 = fetch_via_chrome_tab()
    if data:
        data["_method"] = "chrome_tab"
        save_cache(data)
        check_and_notify(data)
        record_history(data)
        data["_trends"] = get_trend(data)
        print(json.dumps(data))
        return

    # Strategy 2b: AppleScript Safari tab
    data, err3 = fetch_via_safari_tab()
    if data:
        data["_method"] = "safari_tab"
        save_cache(data)
        check_and_notify(data)
        record_history(data)
        data["_trends"] = get_trend(data)
        print(json.dumps(data))
        return

    # Strategy 3: cached data
    cached = load_cache()
    if cached:
        cached["_stale"] = True
        cached["_error"] = f"cookies: {err1} | chrome: {err2} | safari: {err3}"
        print(json.dumps(cached))
        return

    # All failed
    out = {
        "error": f"All methods failed — {err1}",
        "_ts": datetime.now().isoformat()
    }
    print(json.dumps(out))

if __name__ == "__main__":
    main()
