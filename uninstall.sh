#!/bin/bash
# ─── Claude Usage Widget Uninstaller ────────────────────────────────

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'
info() { echo -e "${GREEN}✓${NC} $1"; }

INSTALL_DIR="$HOME/.claude-widget"
WIDGET_FILE="$HOME/Library/Application Support/Übersicht/widgets/claude-usage.jsx"
CACHE_FILE="/tmp/claude_usage_cache.json"

echo ""
echo -e "${BOLD}Claude Usage Widget — Uninstaller${NC}"
echo ""

read -p "Remove Claude Usage Widget? (y/N): " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }

[ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR" && info "Removed $INSTALL_DIR"
[ -f "$WIDGET_FILE" ] && rm -f "$WIDGET_FILE" && info "Removed Übersicht widget"
[ -f "$CACHE_FILE" ] && rm -f "$CACHE_FILE" && info "Removed cache"

echo ""
echo -e "${GREEN}Done!${NC} Widget fully removed."
echo ""
