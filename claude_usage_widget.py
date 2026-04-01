#!/usr/bin/env python3
"""
Claude Usage Desktop Widget for macOS
Shows Claude AI usage limits as a floating desktop widget.
Fetches data via Chrome's active session using AppleScript.
"""

import tkinter as tk
import subprocess
import json
import threading
import time
import os
from datetime import datetime, timezone

# ─── Config ───────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
try:
    with open(CONFIG_FILE, 'r') as _f:
        _cfg = json.load(_f)
except Exception:
    _cfg = {}
ORG_ID = _cfg.get("org_id", "")
REFRESH_INTERVAL_SECONDS = 120  # Refresh every 2 minutes
WIDGET_WIDTH = 320
WIDGET_OPACITY = 0.92
CORNER_RADIUS = 16

# Colors (Dark theme)
BG_COLOR = "#1a1a2e"
CARD_BG = "#16213e"
TEXT_COLOR = "#e8e8e8"
SUBTEXT_COLOR = "#8b8fa3"
ACCENT_SESSION = "#4fc3f7"
ACCENT_WEEKLY = "#7c4dff"
ACCENT_SONNET = "#00e676"
PROGRESS_BG = "#2a2a4a"
HEADER_COLOR = "#ffffff"
BORDER_COLOR = "#2a2a4a"


def fetch_usage():
    """Fetch Claude usage data by running fetch_usage.py (triple fallback)."""
    fetch_script = os.path.join(SCRIPT_DIR, "fetch_usage.py")
    try:
        result = subprocess.run(
            ["python3", fetch_script],
            capture_output=True, text=True, timeout=45
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        return {"error": result.stderr.strip()[:60] or "No data returned"}
    except subprocess.TimeoutExpired:
        return {"error": "Timeout fetching data"}
    except json.JSONDecodeError:
        return {"error": "Invalid response"}
    except Exception as e:
        return {"error": str(e)[:60]}


def time_until_reset(reset_iso):
    """Calculate human-readable time until reset."""
    if not reset_iso:
        return ""
    try:
        reset_time = datetime.fromisoformat(reset_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = reset_time - now
        total_seconds = int(diff.total_seconds())
        if total_seconds <= 0:
            return "Resetting..."
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 24:
            days = hours // 24
            hours = hours % 24
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return ""


class UsageWidget:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Claude Usage")
        self.root.overrideredirect(True)  # Remove title bar
        self.root.attributes("-topmost", True)  # Always on top
        self.root.attributes("-alpha", WIDGET_OPACITY)

        # Position: bottom-right corner
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - WIDGET_WIDTH - 20
        y = screen_h - 420
        self.root.geometry(f"{WIDGET_WIDTH}x400+{x}+{y}")

        # Make window background transparent-ish
        self.root.configure(bg=BG_COLOR)

        # Enable dragging
        self._drag_data = {"x": 0, "y": 0}
        self.root.bind("<Button-1>", self._on_drag_start)
        self.root.bind("<B1-Motion>", self._on_drag_motion)

        # Double-click to refresh
        self.root.bind("<Double-Button-1>", lambda e: self._refresh_data())

        # Right-click to quit
        self.root.bind("<Button-2>", lambda e: self.root.quit())
        self.root.bind("<Button-3>", lambda e: self.root.quit())

        self._build_ui()
        self._refresh_data()

    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Build the widget UI."""
        self.main_frame = tk.Frame(self.root, bg=BG_COLOR, padx=16, pady=12)
        self.main_frame.pack(fill="both", expand=True)

        # Header
        header_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            header_frame, text="⚡", font=("SF Pro", 18),
            bg=BG_COLOR, fg=ACCENT_SESSION
        ).pack(side="left")

        tk.Label(
            header_frame, text=" Claude Usage", font=("SF Pro Display", 16, "bold"),
            bg=BG_COLOR, fg=HEADER_COLOR
        ).pack(side="left")

        self.status_label = tk.Label(
            header_frame, text="●", font=("SF Pro", 10),
            bg=BG_COLOR, fg="#4caf50"
        )
        self.status_label.pack(side="right")

        # Separator
        tk.Frame(self.main_frame, bg=BORDER_COLOR, height=1).pack(fill="x", pady=(0, 12))

        # Session card
        self.session_frame = self._create_usage_card(
            "Current Session", ACCENT_SESSION, "session"
        )

        # Weekly All Models card
        self.weekly_frame = self._create_usage_card(
            "Weekly - All Models", ACCENT_WEEKLY, "weekly"
        )

        # Sonnet card
        self.sonnet_frame = self._create_usage_card(
            "Weekly - Sonnet", ACCENT_SONNET, "sonnet"
        )

        # Footer
        self.footer_label = tk.Label(
            self.main_frame, text="Double-click to refresh  •  Right-click to close",
            font=("SF Pro", 9), bg=BG_COLOR, fg=SUBTEXT_COLOR
        )
        self.footer_label.pack(pady=(8, 0))

        self.updated_label = tk.Label(
            self.main_frame, text="",
            font=("SF Pro", 9), bg=BG_COLOR, fg=SUBTEXT_COLOR
        )
        self.updated_label.pack(pady=(2, 0))

    def _create_usage_card(self, title, accent_color, tag):
        """Create a usage card with progress bar."""
        card = tk.Frame(self.main_frame, bg=CARD_BG, padx=12, pady=10,
                       highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))

        # Title row
        title_frame = tk.Frame(card, bg=CARD_BG)
        title_frame.pack(fill="x")

        tk.Label(
            title_frame, text=title, font=("SF Pro", 11, "bold"),
            bg=CARD_BG, fg=TEXT_COLOR
        ).pack(side="left")

        pct_label = tk.Label(
            title_frame, text="--", font=("SF Pro Rounded", 13, "bold"),
            bg=CARD_BG, fg=accent_color
        )
        pct_label.pack(side="right")
        setattr(self, f"{tag}_pct_label", pct_label)

        # Progress bar
        bar_frame = tk.Frame(card, bg=PROGRESS_BG, height=8)
        bar_frame.pack(fill="x", pady=(6, 4))
        bar_frame.pack_propagate(False)

        bar_fill = tk.Frame(bar_frame, bg=accent_color, height=8)
        bar_fill.place(relx=0, rely=0, relwidth=0, relheight=1)
        setattr(self, f"{tag}_bar_fill", bar_fill)

        # Reset time
        reset_label = tk.Label(
            card, text="", font=("SF Pro", 9),
            bg=CARD_BG, fg=SUBTEXT_COLOR, anchor="w"
        )
        reset_label.pack(fill="x")
        setattr(self, f"{tag}_reset_label", reset_label)

        return card

    def _update_card(self, tag, utilization, reset_time, accent_color):
        """Update a usage card with new data."""
        pct_label = getattr(self, f"{tag}_pct_label")
        bar_fill = getattr(self, f"{tag}_bar_fill")
        reset_label = getattr(self, f"{tag}_reset_label")

        pct = utilization if utilization is not None else 0
        pct_label.config(text=f"{pct}%")

        # Color warning if usage is high
        if pct >= 80:
            pct_label.config(fg="#ff5252")
            bar_fill.config(bg="#ff5252")
        elif pct >= 60:
            pct_label.config(fg="#ffab40")
            bar_fill.config(bg="#ffab40")
        else:
            pct_label.config(fg=accent_color)
            bar_fill.config(bg=accent_color)

        bar_fill.place(relwidth=max(pct / 100, 0.01))

        time_str = time_until_reset(reset_time)
        if time_str:
            reset_label.config(text=f"⏱ Resets in {time_str}")
        else:
            reset_label.config(text="")

    def _refresh_data(self):
        """Fetch and update usage data in a background thread."""
        self.status_label.config(fg="#ffab40")  # Yellow = loading

        def do_fetch():
            data = fetch_usage()
            self.root.after(0, lambda: self._apply_data(data))

        thread = threading.Thread(target=do_fetch, daemon=True)
        thread.start()

        # Schedule next refresh
        self.root.after(REFRESH_INTERVAL_SECONDS * 1000, self._refresh_data)

    def _apply_data(self, data):
        """Apply fetched data to the UI."""
        if "error" in data:
            self.status_label.config(fg="#ff5252")  # Red = error
            self.updated_label.config(text=f"Error: {data['error'][:40]}")
            return

        self.status_label.config(fg="#4caf50")  # Green = OK

        # Session
        five_hour = data.get("five_hour", {})
        self._update_card(
            "session",
            five_hour.get("utilization", 0),
            five_hour.get("resets_at"),
            ACCENT_SESSION
        )

        # Weekly all models
        seven_day = data.get("seven_day", {})
        self._update_card(
            "weekly",
            seven_day.get("utilization", 0),
            seven_day.get("resets_at"),
            ACCENT_WEEKLY
        )

        # Sonnet (only show if data exists — Max plan only)
        sonnet = data.get("seven_day_sonnet")
        if sonnet and isinstance(sonnet, dict):
            self.sonnet_frame.pack(fill="x", pady=(0, 8))
            self._update_card(
                "sonnet",
                sonnet.get("utilization", 0),
                sonnet.get("resets_at"),
                ACCENT_SONNET
            )
        else:
            self.sonnet_frame.pack_forget()

        now = datetime.now().strftime("%H:%M:%S")
        self.updated_label.config(text=f"Updated at {now}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    widget = UsageWidget()
    widget.run()
