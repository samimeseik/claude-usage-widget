# Claude Usage Widget

A macOS desktop widget that shows your Claude AI usage in real-time with notifications, trends, and multi-browser support.

## Features

- **Live usage bars** — Session (5h), Weekly (7d), Sonnet with color-coded thresholds
- **Trend arrows** — ↑ ↓ show if usage is rising or falling vs last check
- **macOS notifications** — Alerts at 80%, 90%, and 100% usage
- **Multi-browser** — Chrome and Safari support
- **Quad fallback** — Cookies → Chrome tab → Safari tab → Cache
- **Auto-update check** — Notifies when a new version is available

## Requirements

- **macOS** (Ventura or later)
- **Google Chrome or Safari** (logged into [claude.ai](https://claude.ai))
- **Claude Pro or Max plan** (Pro shows 2 cards, Max shows 3)
- **Python 3.9+** (pre-installed on macOS)

Optional: [Übersicht](https://tracesof.net/uebersicht/) for the desktop widget.

## Install

```bash
git clone https://github.com/samimeseik/claude-usage-widget.git
cd claude-usage-widget
bash install.sh
```

The installer will:
1. Install Python dependencies (`curl_cffi`, `cryptography`)
2. Auto-detect your Claude organization ID from Chrome
3. Set up the widget at `~/.claude-widget/`
4. Install the Übersicht widget (if Übersicht is installed)

## Uninstall

```bash
bash uninstall.sh
```

## Usage Modes

### Desktop Widget (Übersicht)
Automatically active if Übersicht is installed. Floating widget refreshes every 2 minutes.

### Standalone Widget (tkinter)
```bash
python3 ~/.claude-widget/claude_usage_widget.py
```
Draggable floating window. Double-click to refresh, right-click to close.

## How It Works

The widget fetches usage data via a quad-fallback strategy:

1. **Chrome Cookies** — Reads session from Chrome's cookie DB (fastest, no browser needed)
2. **Chrome Tab** — Executes JS in an open claude.ai Chrome tab
3. **Safari Tab** — Executes JS in an open claude.ai Safari tab
4. **Cache** — Returns last known good data with a "stale" indicator

No API keys needed. No passwords stored. Uses your existing browser session.

## Notifications

macOS notifications fire when usage crosses thresholds:

| Threshold | Notification |
|-----------|-------------|
| 80%+ | "Claude Usage — High Usage" |
| 90%+ | "Claude Usage — Almost Full" |
| 100% | "Claude Usage — Limit Reached" |

Notifications are rate-limited to once per 30 minutes per threshold.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No session cookie" | Log into claude.ai in Chrome or Safari |
| "Run install.sh first" | Run `bash install.sh` |
| Orange dot | Data is cached/stale — will refresh next cycle |
| Red dot | All fetch methods failed — open a browser with claude.ai |

## Config

Stored at `~/.claude-widget/config.json`:
```json
{
    "org_id": "your-org-uuid",
    "cache_path": "/tmp/claude_usage_cache.json"
}
```

## License

MIT
