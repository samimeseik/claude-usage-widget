# Claude Usage Widget

A macOS desktop widget that shows your Claude AI usage in real-time with notifications, trends, and multi-browser support.

## Two widgets, separate concerns

The widget ships as **two separate Übersicht widgets** that share the same backend. Place them on opposite sides of the screen — neither one ever runs off-screen.

| Widget | Position | Shows |
|--------|----------|-------|
| `claude-usage.jsx` | bottom-left | Usage bars (Session, Weekly, Sonnet, Extra Usage), multi-account, sparklines, ETA |
| `claude-code.jsx` | bottom-right | Claude Code dashboard: today, 7-day projects, year heatmap, hourly distribution, agents/skills leaderboard |

You can enable either or both from Übersicht's menu bar icon.

## Features

- **Live usage bars** — Session (5h), Weekly (7d), Sonnet with color-coded thresholds
- **Multi-account** — Track all your Claude organizations in one widget (Personal + Work + API)
- **Claude Code dashboard** — Today's tokens, 7-day project breakdown, year heatmap, hourly distribution, top agents/skills (reads `~/.claude/projects/*.jsonl` directly — no extra fetches)
- **Sparkline trends** — Last 12 hours of usage drawn under each card
- **ETA predictions** — "Reaches 100% at 8:42 PM" when burn rate is rising
- **Absolute reset times** — "resets Thu 8 PM" instead of vague "1d 5h"
- **Extra Usage card** — Shows pay-as-you-go credits used vs monthly limit
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

## Multi-account

If you have multiple Claude organizations (e.g. Personal + Work + an API/eval org), the widget can track them all. The primary account gets the full usage bars; others appear as a compact summary row.

### Auto-discover accounts

```bash
python3 ~/.claude-widget/discover_accounts.py
```

This lists every org accessible from your Chrome session and prints a ready-to-paste config. To save it directly:

```bash
python3 ~/.claude-widget/discover_accounts.py --save
```

### Multi-account config

```json
{
    "accounts": [
        {"org_id": "uuid-1", "label": "Personal", "primary": true},
        {"org_id": "uuid-2", "label": "Work"}
    ],
    "cache_path": "/tmp/claude_usage_cache.json"
}
```

Notes:
- Exactly one account should be marked `primary: true`. If none is marked, the first becomes primary.
- Each account has its own cache + history files (no cross-contamination).
- Accounts that don't expose `/usage` (e.g. some API-only orgs return 403) show as "unavailable" instead of breaking the widget.

## Customizing widgets — position, size, sections

Both widgets are fully configurable from `~/.claude-widget/config.json`. Edit the `widgets` block to change where each one sits, how wide it is, and which sections it shows.

### Full config reference

```json
{
    "accounts": [...],
    "cache_path": "/tmp/claude_usage_cache.json",
    "widgets": {
        "usage": {
            "enabled": true,
            "anchor":  {"vertical": "bottom", "horizontal": "left"},
            "offset":  {"x": 24, "y": 24},
            "width":   280,
            "show":    ["session", "weekly", "sonnet", "extra", "other_accounts", "code_summary"]
        },
        "code": {
            "enabled": true,
            "anchor":  {"vertical": "bottom", "horizontal": "right"},
            "offset":  {"x": 24, "y": 24},
            "width":   300,
            "show":    ["today", "projects_7d", "heatmap", "hourly", "leaderboard"]
        }
    }
}
```

| Field | Values | Effect |
|-------|--------|--------|
| `enabled` | `true` / `false` | Render the widget at all |
| `anchor.vertical` | `"top"` / `"bottom"` | Pin to top or bottom of screen |
| `anchor.horizontal` | `"left"` / `"right"` | Pin to left or right edge |
| `offset.x` | pixels | Distance from horizontal edge |
| `offset.y` | pixels | Distance from vertical edge |
| `width` | pixels | Widget width |
| `show` | array of section names | Which sections render (and order doesn't matter — sections render in their natural order) |

### Section names

**`usage` widget** — `"session"`, `"weekly"`, `"sonnet"`, `"extra"`, `"other_accounts"`, `"code_summary"`

**`code` widget** — `"today"`, `"projects_7d"`, `"heatmap"`, `"hourly"`, `"leaderboard"`

To **hide** a section, just remove its name from the `show` array. To **enable only what you need** (e.g. minimal mode showing only the session bar):

```json
"usage": {
    "show": ["session"]
}
```

### Common layouts

**Minimal**: just the session % in the top-right corner
```json
"usage": {
    "anchor": {"vertical": "top", "horizontal": "right"},
    "offset": {"x": 16, "y": 60},
    "width": 220,
    "show": ["session"]
}
```

**Compact dashboard**: usage bars top-left, no Claude Code dashboard
```json
"usage": {"anchor": {"vertical": "top", "horizontal": "left"}, "offset": {"x": 24, "y": 60}},
"code":  {"enabled": false}
```

**Heatmap-only on the right**: just the year activity graph
```json
"code": {
    "anchor": {"vertical": "bottom", "horizontal": "right"},
    "show": ["today", "heatmap"]
}
```

**Apply changes:** edit `config.json`, save, wait ≤2 minutes for the next refresh (or open Übersicht and click "Refresh All Widgets").

## Config

Single-account config (created by `install.sh`):
```json
{
    "org_id": "your-org-uuid",
    "cache_path": "/tmp/claude_usage_cache.json"
}
```

## License

MIT
