# Claude Usage Widget

A macOS desktop widget that shows your Claude AI usage in real-time.

## What It Shows

- **Current Session** — 5-hour usage window with reset countdown
- **Weekly All Models** — 7-day usage across all models
- **Weekly Sonnet** — Sonnet-specific weekly usage

Color-coded bars: blue/purple (normal) → orange (60%+) → red (80%+).

## Requirements

- **macOS** (Ventura or later)
- **Google Chrome** (logged into [claude.ai](https://claude.ai))
- **Claude Pro or Max plan** (Pro shows 2 cards, Max shows 3)
- **Python 3.9+** (pre-installed on macOS)

Optional: [Übersicht](https://tracesof.net/uebersicht/) for the menu bar widget.

## Install

```bash
bash install.sh
```

That's it. The installer will:
1. Install Python dependencies (`curl_cffi`, `cryptography`)
2. Auto-detect your Claude organization ID from Chrome
3. Set up the widget at `~/.claude-widget/`
4. Install the Übersicht widget (if Übersicht is installed)

## Usage Modes

### Menu Bar Widget (Übersicht)
Automatically starts if Übersicht is installed. Shows a floating widget on your desktop that refreshes every 2 minutes.

### Standalone Widget (tkinter)
```bash
python3 ~/.claude-widget/claude_usage_widget.py
```
A draggable floating window. Double-click to refresh, right-click to close.

## How It Works

The widget fetches your usage data from Claude's API using a triple-fallback strategy:

1. **Chrome Cookies** — Reads your session directly from Chrome's cookie database (fastest)
2. **Chrome Tab** — Executes JavaScript in an open claude.ai tab via AppleScript
3. **Cache** — Falls back to last known good data with a "stale" indicator

No API keys needed. No passwords stored. It uses your existing Chrome session.

## Uninstall

```bash
rm -rf ~/.claude-widget
rm ~/Library/Application\ Support/Übersicht/widgets/claude-usage.jsx
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No session cookie" | Open chrome and log into claude.ai |
| "Run install.sh first" | Run `bash install.sh` |
| Widget shows orange dot | Data is cached/stale — will refresh on next cycle |
| Red dot | All fetch methods failed — check Chrome is running |

## Config

Config is stored at `~/.claude-widget/config.json`:
```json
{
    "org_id": "your-org-uuid",
    "cache_path": "/tmp/claude_usage_cache.json"
}
```

## License

MIT
