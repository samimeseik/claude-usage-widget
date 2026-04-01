#!/bin/bash
set -e

# ─── Claude Usage Widget Installer ─────────────────────────────────
# One-command setup for macOS. Requires: Chrome + Claude Pro or Max plan.
# Usage: bash install.sh

INSTALL_DIR="$HOME/.claude-widget"
WIDGET_DIR="$HOME/Library/Application Support/Übersicht/widgets"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

info()  { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }
step()  { echo -e "\n${BOLD}→ $1${NC}"; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Claude Usage Widget — Installer    ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# ─── Step 1: Preflight checks ──────────────────────────────────────
step "Checking prerequisites..."

[[ "$(uname)" == "Darwin" ]] || fail "This widget is macOS only."
info "macOS detected"

command -v python3 &>/dev/null || fail "python3 not found. Install from python.org or: brew install python"
info "python3 found ($(python3 --version 2>&1 | awk '{print $2}'))"

if [ -d "/Applications/Google Chrome.app" ]; then
    info "Google Chrome found"
else
    fail "Google Chrome not found. Install from google.com/chrome"
fi

HAS_UBERSICHT=false
if [ -d "/Applications/Übersicht.app" ] || [ -d "$HOME/Applications/Übersicht.app" ]; then
    HAS_UBERSICHT=true
    info "Übersicht found"
else
    warn "Übersicht not found — widget will work as standalone (tkinter mode)"
    warn "For menu bar widget, install from: tracesof.net/uebersicht"
fi

# ─── Step 2: Install Python dependencies ───────────────────────────
step "Installing Python dependencies..."

install_deps() {
    if python3 -c "from curl_cffi import requests; from cryptography.hazmat.primitives.ciphers import Cipher" 2>/dev/null; then
        info "Dependencies already installed"
        return 0
    fi

    # Try pip install with --user first
    if pip3 install --user curl_cffi cryptography 2>/dev/null; then
        info "Installed via pip3 --user"
        return 0
    fi

    # macOS 14+ may need --break-system-packages
    if pip3 install --user --break-system-packages curl_cffi cryptography 2>/dev/null; then
        info "Installed via pip3 (with system packages flag)"
        return 0
    fi

    fail "Could not install Python deps. Try manually: pip3 install curl_cffi cryptography"
}
install_deps

# ─── Step 3: Detect ORG_ID ─────────────────────────────────────────
step "Detecting your Claude organization ID..."

detect_org_id() {
    python3 << 'PYEOF'
import sqlite3, shutil, tempfile, json, os, re, subprocess, hashlib, sys

COOKIE_DB = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies")

def get_cookies():
    result = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", "Chrome Safe Storage"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {}
    key = result.stdout.strip()
    dk = hashlib.pbkdf2_hmac('sha1', key.encode('utf-8'), b'saltysalt', 1003, dklen=16)
    if not os.path.exists(COOKIE_DB):
        return {}
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    shutil.copy2(COOKIE_DB, tmp.name)
    cookies = {}
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        conn = sqlite3.connect(tmp.name)
        cur = conn.cursor()
        cur.execute('SELECT name, encrypted_value FROM cookies WHERE host_key IN (".claude.ai","claude.ai")')
        for name, enc in cur.fetchall():
            if not enc: continue
            if enc[:3] == b'v10': enc = enc[3:]
            cipher = Cipher(algorithms.AES(dk), modes.CBC(b' ' * 16), backend=default_backend())
            dec = cipher.decryptor()
            d = dec.update(enc) + dec.finalize()
            pad = d[-1]
            if isinstance(pad, int) and 1 <= pad <= 16: d = d[:-pad]
            raw = d.decode('latin-1')
            m = re.search(r'(sk-ant-\S+)', raw)
            if m: cookies[name] = m.group(1); continue
            m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', raw)
            if m: cookies[name] = m.group(1); continue
            parts = re.findall(r'([!-~]{8,})', raw)
            if parts: cookies[name] = max(parts, key=len)
        conn.close()
    except Exception:
        pass
    finally:
        os.unlink(tmp.name)
    return cookies

cookies = get_cookies()
if 'sessionKey' not in cookies:
    print("NO_SESSION")
    sys.exit(0)

try:
    from curl_cffi import requests
    resp = requests.get(
        "https://claude.ai/api/organizations",
        cookies=cookies, impersonate="chrome", timeout=15
    )
    if resp.status_code == 200:
        orgs = resp.json()
        if isinstance(orgs, list) and len(orgs) > 0:
            for org in orgs:
                print(f"{org.get('uuid','')}|{org.get('name','Unknown')}")
        else:
            print("NO_ORGS")
    else:
        print("API_ERROR")
except Exception as e:
    print(f"ERROR|{e}")
PYEOF
}

ORG_ID=""
ORG_RESULT=$(detect_org_id 2>/dev/null)

if [[ "$ORG_RESULT" == "NO_SESSION" ]] || [[ "$ORG_RESULT" == "API_ERROR" ]] || [[ "$ORG_RESULT" == "NO_ORGS" ]] || [[ "$ORG_RESULT" == ERROR* ]] || [[ -z "$ORG_RESULT" ]]; then
    warn "Could not auto-detect your organization ID."
    echo ""
    echo "To find it manually:"
    echo "  1. Open claude.ai in Chrome"
    echo "  2. Go to Settings → Usage"
    echo "  3. Open Developer Tools (Cmd+Option+I) → Network tab"
    echo "  4. Look for a request to /api/organizations/*/usage"
    echo "  5. Copy the UUID from the URL"
    echo ""
    read -p "Paste your Organization ID: " ORG_ID
    [[ -n "$ORG_ID" ]] || fail "No organization ID provided."
else
    # Parse orgs
    ORG_COUNT=$(echo "$ORG_RESULT" | wc -l | tr -d ' ')
    if [[ "$ORG_COUNT" -eq 1 ]]; then
        ORG_ID=$(echo "$ORG_RESULT" | cut -d'|' -f1)
        ORG_NAME=$(echo "$ORG_RESULT" | cut -d'|' -f2)
        info "Found organization: $ORG_NAME"
    else
        echo "Found multiple organizations:"
        # Store orgs in arrays
        declare -a ORG_IDS=()
        declare -a ORG_NAMES=()
        i=1
        while IFS='|' read -r uuid name; do
            ORG_IDS+=("$uuid")
            ORG_NAMES+=("$name")
            echo "  $i) $name"
            i=$((i+1))
        done <<< "$ORG_RESULT"
        echo ""
        read -p "Select organization (1-$ORG_COUNT): " CHOICE
        # Validate choice is a number in range
        if [[ "$CHOICE" =~ ^[0-9]+$ ]] && [[ "$CHOICE" -ge 1 ]] && [[ "$CHOICE" -le "$ORG_COUNT" ]]; then
            IDX=$((CHOICE - 1))
            ORG_ID="${ORG_IDS[$IDX]}"
            info "Selected: ${ORG_NAMES[$IDX]}"
        else
            fail "Invalid selection: $CHOICE"
        fi
    fi
fi

[[ -n "$ORG_ID" ]] || fail "No organization ID."
info "Organization ID: ${ORG_ID:0:8}...${ORG_ID: -4}"

# ─── Step 4: Install files ─────────────────────────────────────────
step "Installing widget to $INSTALL_DIR..."

mkdir -p "$INSTALL_DIR"

# Write config
cat > "$INSTALL_DIR/config.json" << JSONEOF
{
    "org_id": "$ORG_ID",
    "cache_path": "/tmp/claude_usage_cache.json"
}
JSONEOF
info "Config saved"

# Copy Python files
cp "$SCRIPT_DIR/fetch_usage.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/claude_usage_widget.py" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/fetch_usage.py"
info "Scripts installed"

# Copy Übersicht widget
if $HAS_UBERSICHT; then
    mkdir -p "$WIDGET_DIR"
    cp "$SCRIPT_DIR/claude-usage.jsx" "$INSTALL_DIR/"
    cp "$INSTALL_DIR/claude-usage.jsx" "$WIDGET_DIR/"
    info "Übersicht widget installed"
fi

# ─── Step 5: Verify ───────────────────────────────────────────────
step "Verifying installation..."

RESULT=$(python3 "$INSTALL_DIR/fetch_usage.py" 2>&1)
if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'five_hour' in d else 1)" 2>/dev/null; then
    info "Data fetch successful!"
    USAGE=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Session: {d['five_hour']['utilization']}% | Weekly: {d['seven_day']['utilization']}%\")")
    echo -e "  ${GREEN}$USAGE${NC}"
else
    warn "Could not fetch data right now (may work on next refresh)"
    warn "Output: ${RESULT:0:100}"
fi

# ─── Done ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║          Installation Complete!       ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo "  Installed to: $INSTALL_DIR"
if $HAS_UBERSICHT; then
    echo "  Übersicht widget: active (refresh with Cmd+R in Übersicht)"
fi
echo ""
echo "  Standalone mode: python3 $INSTALL_DIR/claude_usage_widget.py"
echo ""
echo "  To uninstall: rm -rf $INSTALL_DIR"
echo ""
