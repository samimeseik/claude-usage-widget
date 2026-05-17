# r/ClaudeAI post

## Title options (pick one)

1. **I built a macOS widget that shows your Claude.ai limits AND Claude Code usage in real time — with a $ value vs your plan**
2. **Built a Mac widget so you never have to open claude.ai/settings/usage again**
3. **My Max plan saves me $2,337/month — I built a widget that tracks this in real time**

Use title #1 — most descriptive, gets the killer features upfront.

## Post body

Hey r/ClaudeAI 👋

I kept opening `claude.ai/settings/usage` 5 times a day to check if I was about to hit my Max limit. Then I'd separately worry about whether my Claude Code sessions were eating my weekly budget. And nowhere could I see, in dollars, whether the $200/mo plan was actually worth it.

So I built a macOS widget that solves all three.

**It's two separate Übersicht widgets** that share a backend:

**Left side — your claude.ai usage:**
- Current session, weekly, and Sonnet bars (color-coded: yellow at 60%, red at 80%)
- Sparklines showing the last 12 hours of usage
- ETA predictions: "Reaches 100% at 8:42 PM" when burn rate is rising
- Reset times in your timezone ("resets Thu 8 PM" not "in 1d 5h")
- Multi-account support (Personal + Work + API orgs)

**Right side — your Claude Code activity:**
- Today's sessions, tokens, top tools, primary project
- 7-day per-project breakdown with mini bar charts
- **1-year heatmap** (GitHub contribution graph style)
- **30-day hourly distribution** — see when you code most (I'm a 5 PM + 2 AM person apparently)
- **Skills + Agents leaderboard** — top sub-agents you spawn, most-used skills
- **💰 API Value card** — what your last 30 days would cost on the raw Anthropic API

That last one is the one I keep showing people. Mine reads:

```
API VALUE · 30D                  vs Max ($200/mo)
$2,537                                  🎉 12.7×
Saved $2,337 vs API · projected this month $2,127
```

For Max plan users this is the single number that answers "is this worth $200/mo?"

**How it gets the data:**
- Reads `~/.claude/projects/*.jsonl` directly for Claude Code stats (no API calls)
- Extracts your Chrome cookie via macOS Keychain, decrypts with PBKDF2 + AES, then hits `claude.ai/api/.../usage` using `curl_cffi` to bypass Cloudflare
- Falls back to Chrome tab JS → Safari tab JS → cached if any step fails
- All data stays on your Mac. No analytics. No telemetry.

**Install:**
```bash
git clone https://github.com/samimeseik/claude-usage-widget.git
cd claude-usage-widget
bash install.sh
```

Customizable via a browser-based settings UI (`python3 ~/.claude-widget/configure.py`) — move widgets between corners, resize, toggle individual sections, all without touching code.

Open source, MIT. Happy to take feature requests in this thread or as GitHub issues.

**Repo:** https://github.com/samimeseik/claude-usage-widget

[attach 2-3 screenshots — main view, settings UI, year heatmap close-up]

## Tone notes

- Don't start with "Hey guys" or "Hi everyone" — start with the problem
- The "Max plan saves me $X" line is the strongest hook — leads with self-interest, not product
- Mention competing tools (ccusage, Maciek-roboblog) by name to signal you did your homework and aren't reinventing wheels
- Reddit hates obvious marketing — keep it personal and useful

## Response strategy

Reply to first 5 comments within an hour. Pin a comment with the install command if it gets traction.

## Best time to post

- Sunday 8-10 PM ET (highest weekly traffic on r/ClaudeAI)
- Or Tuesday 10 AM ET
