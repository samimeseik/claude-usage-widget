# Claude Usage Widget

> The first macOS widget that shows your **claude.ai usage AND Claude Code activity** in one glance — with a real-time dollar value vs your subscription.

<p align="center">
  <!-- TODO: replace with real screenshot -->
  <img src=".github/hero.png" alt="Claude Usage Widget on macOS desktop" width="800" />
</p>

<p align="center">
  <a href="https://github.com/samimeseik/claude-usage-widget/releases"><img src="https://img.shields.io/github/v/release/samimeseik/claude-usage-widget" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" /></a>
  <img src="https://img.shields.io/badge/macOS-13%2B-black?logo=apple" />
  <img src="https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white" />
</p>

---

## Why this exists

Every other Claude usage tracker picks a side:
- 🌐 **claude.ai trackers** (Maciek-roboblog, lugia19) show plan limits but ignore Claude Code
- 💻 **Claude Code trackers** (ccusage) read `.jsonl` files but ignore your claude.ai subscription
- 📊 **Anthropic's own dashboard** is buried 4 clicks deep in settings, gives you percentages without context, and has no historical view

This widget shows **both** in one glanceable view — and the killer feature: it tells you in **dollars** what you'd pay on the raw API for what you actually use. For Max plan users this answers the single most useful question: *"is $200/mo worth it?"*

A typical heavy user sees something like:

```
API VALUE · 30D                  vs Max ($200/mo)

$2,537                                  🎉 12.7×

Saved $2,337 vs API · projected this month $2,127
```

---

## Features

### 📊 The Usage widget (left side)
- **Session / Weekly / Sonnet bars** with color-coded thresholds (yellow at 60%, red at 80%)
- **Sparklines** — last 12 hours of usage drawn under each bar
- **ETA predictions** — *"Reaches 100% at 8:42 PM"* when burn rate is rising
- **Absolute reset times** — *"resets Thu 8 PM"* instead of vague *"1d 5h"*
- **Extra Usage card** — pay-as-you-go credits used vs monthly limit
- **Trend arrows** ↑ ↓ — usage rising or falling vs last check
- **Multi-account** — Personal + Work + API orgs in one widget

### 💻 The Claude Code widget (right side)
- **Today** — tokens, sessions, top tools, primary project
- **7-day project breakdown** — see where your week's tokens went
- **1-year heatmap** — GitHub-style contribution graph for Claude Code
- **30-day hourly distribution** — when in the day you're most active
- **Skills + Agents leaderboard** — top sub-agents (Explore, Plan, etc.) and skills (your most-invoked)
- **💰 API Value card** — what your usage would cost on the API, with a multiplier vs your plan

### 🔔 Plus
- **macOS notifications** at 80%, 90%, 100%
- **Quad fallback fetch**: Chrome cookies → Chrome tab → Safari tab → cached
- **Auto-update check** — notifies when a new version ships
- **Visual settings UI** — no JSON editing, browser-based control panel

---

## Install (one command)

```bash
git clone https://github.com/samimeseik/claude-usage-widget.git
cd claude-usage-widget
bash install.sh
```

The installer:
1. Checks prerequisites (macOS, Chrome, Python, Übersicht)
2. Auto-detects your Claude org ID from Chrome
3. Installs `pip` dependencies (`curl_cffi`, `cryptography`)
4. Copies both widgets to `~/Library/Application Support/Übersicht/widgets/`
5. Runs a verification fetch

Open Übersicht's menu bar icon to toggle each widget on.

### Requirements

- **macOS 13+** (Ventura or later)
- **Google Chrome or Safari** (logged into [claude.ai](https://claude.ai))
- **Claude Pro / Max / Teams plan**
- **Python 3.9+** (pre-installed on macOS)
- **[Übersicht](https://tracesof.net/uebersicht/)** (free)

---

## Customize without editing code

Launch the visual settings UI:

```bash
python3 ~/.claude-widget/configure.py
```

Or double-click `~/.claude-widget/configure.command` from Finder.

A page opens at `http://localhost:7777/` where you can:
- Enable / disable each widget
- Pick any of the 4 corner anchors (top-left, top-right, bottom-left, bottom-right)
- Adjust offset X/Y and width via sliders
- Toggle individual sections (heatmap, leaderboard, etc.)

Save → widgets refresh within ~1 second.

<p align="center">
  <!-- TODO: replace with real settings UI screenshot -->
  <img src=".github/settings.png" alt="Visual settings UI" width="600" />
</p>

---

## Multi-account

If you have multiple Claude organizations (Personal + Work + API/eval), the widget tracks them all:

```bash
python3 ~/.claude-widget/discover_accounts.py --save
```

The script lists every org accessible from your Chrome session and writes a ready-to-go multi-account config. Primary account gets full usage bars; others appear as a compact summary row.

---

## How it works

```
┌───────────────────────────────────────────────────────┐
│   fetch_usage.py (every 2 min, via Übersicht)         │
│                                                       │
│   1. Cookie + curl_cffi  →  claude.ai/api/.../usage   │
│   2. Chrome tab JS       (fallback)                   │
│   3. Safari tab JS       (fallback)                   │
│   4. Cache               (last-known-good)            │
│                                                       │
│   + code_stats.py walks ~/.claude/projects/*.jsonl    │
│     for Claude Code stats (today, 7d, year, hourly)   │
└───────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        claude-usage.jsx        claude-code.jsx
        (left widget)           (right widget)
```

- **Cookie extraction**: reads Chrome's encrypted cookie store via macOS Keychain, decrypts with PBKDF2-derived AES key, bypasses Cloudflare with `curl_cffi`'s Chrome-impersonation TLS fingerprint
- **No browser required**: cookies work standalone; Chrome doesn't even need to be open
- **No data leaves your machine**: all fetches go directly to claude.ai with your own session
- **Caches everything**: heatmap (1h), hourly (1h), leaderboard (1h), cost (1h), main usage (2 min)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No session cookie" | Log into claude.ai in Chrome or Safari once |
| "Run install.sh first" | Run `bash install.sh` |
| Position changes don't apply | Quit + relaunch Übersicht once after upgrade |
| Orange dot in widget header | Data is cached — will refresh next cycle |
| Red dot in widget header | All fetch methods failed — open a browser with claude.ai |
| 403 for an API/eval org | That org doesn't expose `/usage` — widget shows "unavailable" gracefully |

---

## Roadmap

- [ ] Calendar heatmap as standalone widget for r/dataisbeautiful screenshots
- [ ] Streak tracker ("12-day Claude Code streak")
- [ ] Per-project drilldown view in browser
- [ ] Export 1-year history as CSV
- [ ] Homebrew formula (`brew install claude-usage-widget`)

Open an issue if there's something you want to see.

---

## Privacy

This widget never sends data anywhere except claude.ai itself (using your own session). All processing, caching, and history happens in `~/.claude-widget/` on your Mac.

- No analytics
- No telemetry
- No external services
- No accounts to create
- Reads only: Chrome cookie store, `~/.claude/projects/*.jsonl`, claude.ai API
- Writes only: `~/.claude-widget/` and `/tmp/claude_usage_cache.json`

---

## License

MIT — do whatever you want.

---

## Credits

Built with [Übersicht](https://tracesof.net/uebersicht/), `curl_cffi`, and `cryptography`. Inspired by [ccusage](https://github.com/ryoppippi/ccusage) (the leading Claude Code tracker) and [Maciek-roboblog's claude-usage](https://github.com/Maciek-roboblog/claude-usage) — combining the best of both worlds.
