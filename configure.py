#!/usr/bin/env python3
"""
Visual config editor for the Claude Usage Widget — runs as a tiny local
HTTP server and opens the settings page in your browser.

Run:
    python3 ~/.claude-widget/configure.py

Or double-click ~/.claude-widget/configure.command from Finder.

Reads ~/.claude-widget/config.json, opens http://localhost:7777/ in the
default browser. Save → server writes config.json + nudges Übersicht to
re-render the widgets immediately.
"""
import json
import os
import sys
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

CONFIG_PATH = os.path.expanduser("~/.claude-widget/config.json")
PORT = 7777

USAGE_SECTIONS = [
    ("session",        "Current Session"),
    ("weekly",         "Weekly — All Models"),
    ("sonnet",         "Weekly — Sonnet"),
    ("extra",          "Extra Usage ($)"),
    ("other_accounts", "Other Accounts"),
    ("code_summary",   "Claude Code summary line"),
]

CODE_SECTIONS = [
    ("today",       "Today (tokens, tools, project)"),
    ("projects_7d", "7-day project breakdown"),
    ("heatmap",     "1-year activity heatmap"),
    ("hourly",      "30-day hourly distribution"),
    ("leaderboard", "Skills + Agents leaderboard"),
    ("value",       "API Value (cost vs plan)"),
]

DEFAULT_WIDGET = {
    "usage": {
        "enabled": True,
        "anchor":  {"vertical": "bottom", "horizontal": "left"},
        "offset":  {"x": 24, "y": 24},
        "width":   280,
        "show":    [k for k, _ in USAGE_SECTIONS],
    },
    "code": {
        "enabled": True,
        "anchor":  {"vertical": "bottom", "horizontal": "right"},
        "offset":  {"x": 24, "y": 24},
        "width":   300,
        "show":    [k for k, _ in CODE_SECTIONS],
    },
}


def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print(f"Error: {CONFIG_PATH} not found. Run install.sh first.")
        sys.exit(1)
    cfg.setdefault("widgets", {})
    for k, defaults in DEFAULT_WIDGET.items():
        existing = cfg["widgets"].get(k) or {}
        merged = json.loads(json.dumps(defaults))
        for kk, vv in existing.items():
            if kk in ("anchor", "offset") and isinstance(vv, dict):
                merged[kk].update(vv)
            else:
                merged[kk] = vv
        cfg["widgets"][k] = merged
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)


def nudge_widgets():
    """Touch the JSX files + spawn a fresh fetch so widgets refresh fast."""
    for name in ("claude-usage.jsx", "claude-code.jsx"):
        p = os.path.expanduser(
            f"~/Library/Application Support/Übersicht/widgets/{name}"
        )
        if os.path.exists(p):
            try:
                os.utime(p, None)
            except Exception:
                pass
    try:
        subprocess.Popen(
            ["python3", os.path.expanduser("~/.claude-widget/fetch_usage.py")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# ─── HTML page ─────────────────────────────────────────────────────

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Claude Usage Widget — Settings</title>
<style>
  :root {
    --bg: #0f1014; --card: #1a1c22; --card2: #20232a;
    --border: #2a2d36; --text: #e8e8ed; --muted: #9aa0a8;
    --accent: #64d2ff; --green: #30d158; --warn: #ff9f0a;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 32px 24px;
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display',
                 'Helvetica Neue', sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.4px; }
  .lede { color: var(--muted); margin: 0 0 24px; font-size: 13px; }
  .tabs { display: flex; gap: 4px; margin-bottom: 16px; }
  .tab {
    padding: 8px 16px; border: 1px solid var(--border); border-radius: 8px;
    background: var(--card); color: var(--muted); cursor: pointer;
    font-size: 13px; font-weight: 600;
  }
  .tab.active { background: var(--accent); color: #001828; border-color: var(--accent); }
  .panel { display: none; }
  .panel.active { display: block; }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px; margin-bottom: 12px;
  }
  .card h3 {
    margin: 0 0 12px; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted);
  }
  .row { display: flex; gap: 12px; align-items: center; margin-bottom: 10px; }
  .row label { flex: 1; font-size: 13px; color: var(--text); }
  .row .value { font-variant-numeric: tabular-nums; color: var(--accent); width: 56px; text-align: right; font-size: 12px; font-weight: 600; }
  select, input[type=range] {
    background: var(--card2); color: var(--text);
    border: 1px solid var(--border); border-radius: 6px;
    padding: 6px 8px; font-size: 13px; font-family: inherit;
  }
  input[type=range] { -webkit-appearance: none; height: 4px; padding: 0; flex: 1; max-width: 240px; }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 14px; height: 14px;
    border-radius: 50%; background: var(--accent); cursor: pointer;
  }
  .check-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px; border-radius: 6px; cursor: pointer;
    transition: background 0.1s;
  }
  .check-row:hover { background: var(--card2); }
  .check-row input { accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer; }
  .check-row span { font-size: 13px; color: var(--text); }
  .corner-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    margin-bottom: 12px;
  }
  .corner-btn {
    padding: 10px; border: 1px solid var(--border); border-radius: 8px;
    background: var(--card2); color: var(--muted); cursor: pointer;
    font-size: 12px; font-weight: 600; text-align: center;
    transition: all 0.15s;
  }
  .corner-btn.active { background: var(--accent); color: #001828; border-color: var(--accent); }
  .footer {
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border);
  }
  .status { color: var(--green); font-size: 13px; font-weight: 500; min-height: 18px; }
  button.primary {
    background: var(--accent); color: #001828; border: none;
    padding: 10px 24px; border-radius: 8px; font-size: 14px;
    font-weight: 700; cursor: pointer; font-family: inherit;
  }
  button.primary:hover { background: #7ddaff; }
  button.secondary {
    background: transparent; color: var(--muted); border: 1px solid var(--border);
    padding: 10px 16px; border-radius: 8px; font-size: 14px;
    cursor: pointer; font-family: inherit; margin-right: 8px;
  }
  button.secondary:hover { color: var(--text); border-color: var(--muted); }
  .toggle-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 14px; background: var(--card2); border-radius: 8px;
    margin-bottom: 12px;
  }
  .toggle-row label { font-weight: 600; cursor: pointer; }
  .toggle-row input { accent-color: var(--accent); width: 18px; height: 18px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Claude Usage Widget</h1>
  <p class="lede">Customize position, size, and which sections each widget shows. Changes apply within seconds.</p>

  <div class="tabs">
    <div class="tab active" data-tab="usage">Usage Widget</div>
    <div class="tab" data-tab="code">Claude Code Widget</div>
  </div>

  <div id="panel-usage" class="panel active"></div>
  <div id="panel-code"  class="panel"></div>

  <div class="footer">
    <div class="status" id="status"></div>
    <div>
      <button class="secondary" onclick="window.close()">Close</button>
      <button class="primary"  id="save-btn">Save</button>
    </div>
  </div>
</div>

<script>
const SECTIONS = {
  usage: __USAGE_SECTIONS__,
  code:  __CODE_SECTIONS__,
};
const CONFIG  = __CONFIG__;

function panelHTML(name, cfg) {
  const sects = SECTIONS[name];
  return `
  <div class="toggle-row">
    <label for="${name}-enabled">Show this widget on the desktop</label>
    <input type="checkbox" id="${name}-enabled" ${cfg.enabled ? 'checked' : ''} />
  </div>

  <div class="card">
    <h3>Position — anchor corner</h3>
    <div class="corner-grid">
      <button class="corner-btn ${cfg.anchor.vertical==='top' && cfg.anchor.horizontal==='left' ? 'active':''}"
              data-w="${name}" data-v="top" data-h="left">↖ Top-left</button>
      <button class="corner-btn ${cfg.anchor.vertical==='top' && cfg.anchor.horizontal==='right' ? 'active':''}"
              data-w="${name}" data-v="top" data-h="right">↗ Top-right</button>
      <button class="corner-btn ${cfg.anchor.vertical==='bottom' && cfg.anchor.horizontal==='left' ? 'active':''}"
              data-w="${name}" data-v="bottom" data-h="left">↙ Bottom-left</button>
      <button class="corner-btn ${cfg.anchor.vertical==='bottom' && cfg.anchor.horizontal==='right' ? 'active':''}"
              data-w="${name}" data-v="bottom" data-h="right">↘ Bottom-right</button>
    </div>

    <div class="row">
      <label>Distance from horizontal edge (X)</label>
      <input type="range" min="0" max="600" step="2" value="${cfg.offset.x}" id="${name}-x" />
      <span class="value"><span id="${name}-x-v">${cfg.offset.x}</span>px</span>
    </div>
    <div class="row">
      <label>Distance from vertical edge (Y)</label>
      <input type="range" min="0" max="600" step="2" value="${cfg.offset.y}" id="${name}-y" />
      <span class="value"><span id="${name}-y-v">${cfg.offset.y}</span>px</span>
    </div>
  </div>

  <div class="card">
    <h3>Width</h3>
    <div class="row">
      <label>Widget width</label>
      <input type="range" min="200" max="480" step="4" value="${cfg.width}" id="${name}-w" />
      <span class="value"><span id="${name}-w-v">${cfg.width}</span>px</span>
    </div>
  </div>

  <div class="card">
    <h3>Sections to show</h3>
    ${sects.map(s => `
      <label class="check-row">
        <input type="checkbox" data-w="${name}" data-s="${s[0]}"
               ${cfg.show.includes(s[0]) ? 'checked' : ''} />
        <span>${s[1]}</span>
      </label>
    `).join('')}
  </div>
  `;
}

function render() {
  document.getElementById('panel-usage').innerHTML = panelHTML('usage', CONFIG.widgets.usage);
  document.getElementById('panel-code').innerHTML  = panelHTML('code',  CONFIG.widgets.code);
  bindControls('usage');
  bindControls('code');
}

function bindControls(name) {
  // Sliders
  ['x', 'y', 'w'].forEach(k => {
    const el = document.getElementById(`${name}-${k}`);
    const lbl = document.getElementById(`${name}-${k}-v`);
    el.addEventListener('input', () => { lbl.textContent = el.value; });
  });
  // Corner buttons
  document.querySelectorAll(`.corner-btn[data-w="${name}"]`).forEach(b => {
    b.addEventListener('click', e => {
      document.querySelectorAll(`.corner-btn[data-w="${name}"]`).forEach(x => x.classList.remove('active'));
      b.classList.add('active');
    });
  });
}

// Tab switching
document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById(`panel-${t.dataset.tab}`).classList.add('active');
  });
});

function collect(name) {
  const v = id => document.getElementById(`${name}-${id}`);
  const activeCorner = document.querySelector(`.corner-btn[data-w="${name}"].active`);
  const sects = Array.from(document.querySelectorAll(`input[type=checkbox][data-w="${name}"][data-s]`))
    .filter(x => x.checked).map(x => x.dataset.s);
  return {
    enabled: document.getElementById(`${name}-enabled`).checked,
    anchor: {
      vertical:   activeCorner.dataset.v,
      horizontal: activeCorner.dataset.h,
    },
    offset: { x: parseInt(v('x').value), y: parseInt(v('y').value) },
    width:  parseInt(v('w').value),
    show:   sects,
  };
}

document.getElementById('save-btn').addEventListener('click', async () => {
  const status = document.getElementById('status');
  const newCfg = {
    widgets: {
      usage: collect('usage'),
      code:  collect('code'),
    }
  };
  status.textContent = '⏳ Saving…';
  try {
    const r = await fetch('/save', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(newCfg),
    });
    if (r.ok) {
      status.textContent = '✓ Saved — widgets refreshing now';
      setTimeout(() => status.textContent = '', 3500);
    } else {
      status.textContent = '✗ Save failed: ' + (await r.text());
      status.style.color = '#ff6b6b';
    }
  } catch (e) {
    status.textContent = '✗ ' + e.message;
    status.style.color = '#ff6b6b';
  }
});

render();
</script>
</body>
</html>
"""


# ─── HTTP server ───────────────────────────────────────────────────


class ConfigHandler(BaseHTTPRequestHandler):
    # Silence default logging
    def log_message(self, *args, **kwargs):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            cfg = load_config()
            html = (INDEX_HTML
                    .replace("__USAGE_SECTIONS__", json.dumps(USAGE_SECTIONS))
                    .replace("__CODE_SECTIONS__", json.dumps(CODE_SECTIONS))
                    .replace("__CONFIG__", json.dumps(cfg)))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path != "/save":
            self.send_response(404); self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body)
            cfg = load_config()
            cfg["widgets"] = payload.get("widgets", cfg["widgets"])
            save_config(cfg)
            nudge_widgets()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))


def main():
    server = HTTPServer(("127.0.0.1", PORT), ConfigHandler)
    print(f"\n  Settings UI running at http://localhost:{PORT}/")
    print("  (Ctrl+C to stop)\n")
    # Open browser after a tiny delay so the server is ready
    threading.Timer(0.6, lambda: webbrowser.open(f"http://localhost:{PORT}/")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  bye.")
        server.shutdown()


if __name__ == "__main__":
    main()
