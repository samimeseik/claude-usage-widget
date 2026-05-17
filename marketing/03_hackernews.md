# Hacker News — Show HN

## Title (the most important thing)

**Show HN: Claude Usage Widget – macOS widget for Claude.ai + Claude Code in one view**

Rules HN cares about:
- Start with "Show HN: "
- Under 80 chars
- No marketing fluff ("amazing", "easy", "powerful")
- Describe what it IS, not what it does for you

## URL field

`https://github.com/samimeseik/claude-usage-widget`

## First comment (post immediately after submission)

> Author here.
>
> I built this because I was tab-switching to claude.ai/settings/usage 5x a day, and separately worrying about whether Claude Code sessions were eating my weekly Max budget. Nowhere could I see both in one place, and nowhere could I see — in dollars — whether the plan was actually worth it.
>
> Two Übersicht widgets sharing a backend:
>
> **Left**: claude.ai usage (session/weekly/sonnet bars with sparklines, ETA predictions, multi-org)
>
> **Right**: Claude Code dashboard (today, 7-day projects, 1-year heatmap, hourly distribution, agents/skills leaderboard, and an API-equivalent cost card)
>
> The cost card is the part I'd flag for HN. It walks `~/.claude/projects/*.jsonl`, prices each assistant message against the published Anthropic API rates (Opus $15/$75, Sonnet $3/$15, etc.) including cache read/write multipliers, and shows you what your last 30d would cost on the raw API. Mine reads $2,537 vs $200 plan = 12.7×.
>
> Tech notes:
>
> - Cookie extraction: reads Chrome's encrypted cookie DB, decrypts with PBKDF2-SHA1 + AES-CBC using the key from macOS Keychain (`Chrome Safe Storage`)
> - Cloudflare bypass: `curl_cffi` impersonates Chrome's TLS fingerprint — works without the browser even being open
> - Quad fallback: cookies → Chrome tab JS → Safari tab JS → cached
> - All caches are local files in `~/.claude-widget/`
> - Heatmap/hourly/leaderboard/cost are computed once per hour from `.jsonl` files (≤350ms for ~31 active days of history)
>
> The configure UI is a tiny stdlib `http.server` on localhost:7777 that serves a single HTML page with form controls — no JS framework, no build step, ~450 lines including the embedded HTML.
>
> Happy to take questions on any of this.

## Why this works on HN

- Clear technical hook (TLS fingerprint, AES-CBC, no framework)
- Lists specific numbers ($, ms)
- Acknowledges related work (`ccusage`, `Maciek-roboblog`) — HN respects honest positioning
- "Author here" + technical detail is the canonical Show HN comment style

## What NOT to do

- Don't editorialize ("Such a cool project!" — instant downvote)
- Don't post-and-run — respond to every question for the first 4 hours
- Don't ask for upvotes (HN bans for that)
- Don't repost if it dies — submissions get one shot
- Avoid the word "AI" in title if possible; HN is jaded

## Best time to post

- Tuesday-Thursday, 8-10 AM ET
- Front page algorithm boosts new submissions for ~2 hours
- Be online to answer comments

## Targets

- Realistic: 30-80 points, top 30 of "show" page
- Optimistic: front page (200+ points)
- The "$2,537 vs $200" line is the most front-page-able hook
