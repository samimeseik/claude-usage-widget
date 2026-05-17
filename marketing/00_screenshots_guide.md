# Screenshot capture guide

For the README hero + marketing posts, you need 3 shots. Here's the recipe.

## Prep (one time)

```bash
# 1. Make sure both widgets are showing with real data
python3 ~/.claude-widget/fetch_usage.py > /tmp/claude_usage_cache.json
open -a "Übersicht"

# 2. Set a clean wallpaper — solid color or muted gradient looks best
# System Settings → Wallpaper → pick a dark solid (e.g. "Black")

# 3. Clean your desktop — drag all icons into one folder temporarily
mkdir -p ~/Desktop/_hidden_for_screenshot
mv ~/Desktop/*.{png,jpg,pdf,zip,dmg,jpeg} ~/Desktop/_hidden_for_screenshot/ 2>/dev/null
```

## Shot 1 — hero.png (for README + Twitter)

**Setup:**
- Both widgets visible on desktop
- Bottom-left = usage widget
- Bottom-right = code widget
- API VALUE card visible in code widget (most striking number)

**Capture:**
```bash
# Full screen
screencapture -x -t png ~/Desktop/hero-full.png
# Or just the bottom portion (Cmd+Shift+4 then drag)
```

For maximum impact: crop to roughly 1600×900px so both widgets are clearly visible but the screen feels "lived in" with a hint of wallpaper.

## Shot 2 — settings.png (for README customization section)

**Setup:**
```bash
python3 ~/.claude-widget/configure.py
```
- Browser opens at `http://localhost:7777/`
- Use Chrome in dark mode if available

**Capture:**
- Cmd+Shift+4, drag the browser window
- Or: Cmd+Shift+4 then Spacebar then click the browser window (clean window grab)

## Shot 3 — heatmap.png (for r/dataisbeautiful + Reddit)

**Setup:**
- Use the configure UI to enable ONLY the heatmap section in the code widget
- This gives a clean shot of just the 1-year graph

**Capture:**
- Cmd+Shift+4 and drag tight around the heatmap card
- Aim for ~500×120px

## Demo GIF (10-15 seconds, optional but high-impact)

```bash
# Built into macOS: Cmd+Shift+5 → record selected portion
```

Show this sequence:
1. Both widgets sitting on desktop (1-2 sec)
2. Open the configure UI (1 sec)
3. Drag the offset slider — widget moves in real time (3 sec)
4. Toggle a section checkbox — widget updates (3 sec)
5. Click Save — done indicator (1 sec)

Convert to GIF after recording:
```bash
# Install ffmpeg if needed
brew install ffmpeg gifski

# Convert .mov to GIF (small file size with gifski)
ffmpeg -i ~/Desktop/demo.mov -vf "fps=12,scale=720:-1:flags=lanczos" -f yuv4mpegpipe - | gifski --fps 12 -o ~/Desktop/demo.gif -
```

Target: under 8 MB so it embeds inline on GitHub README.

## Where to put the files

```
.github/
├── hero.png          # 1600×900, README hero + Twitter
├── settings.png      # 900×700, README settings section
├── heatmap.png       # 500×120, Reddit datavis-style
└── demo.gif          # 720px wide, README + Twitter pinned tweet
```

After capture, commit:
```bash
cd ~/Desktop/ClaudeUsageWidget
git add .github/
git commit -m "docs: add screenshots and demo GIF"
git push
```

## Restore desktop

```bash
mv ~/Desktop/_hidden_for_screenshot/* ~/Desktop/
rmdir ~/Desktop/_hidden_for_screenshot
```
