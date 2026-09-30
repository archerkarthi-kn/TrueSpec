"""
TrueSpec: Second-Hand Laptop Inspector
Module: screen_keyboard_test.py
Author: TrueSpec Core Systems Team

Interactive full-screen dead pixel, subpixel fault, and backlight bleed tester.
Features:
- Solid primary & secondary color planes for deep LCD inspection
- Toggleable 1px alignment grid to locate and count dead subpixels
- Always-visible top-right "✕ Exit" button & bottom navigation HUD
- Failsafe key bindings: ESC, Q, X, Right-Click, or Double-Click to exit
- Restores mouse pointer so users never feel trapped
"""

import sys
import tkinter as tk
from typing import Optional


class DeadPixelTester:
    """
    High-performance, full-screen LCD inspection utility.
    Cycles solid colors, provides subpixel verification, and ensures
    foolproof exit controls under all conditions.
    """

    COLOR_PALETTE = [
        ("#FF0000", "Pure Red", "Check for dead/stuck RED subpixels"),
        ("#00FF00", "Pure Green", "Check for dead/stuck GREEN subpixels"),
        ("#0000FF", "Pure Blue", "Check for dead/stuck BLUE subpixels"),
        ("#FFFFFF", "Pure White", "Check for dead pixels (dark spots) & dust specks"),
        ("#000000", "Pure Black", "Check for backlight bleed, IPS glow & bright stuck pixels"),
        ("#808080", "50% Uniform Gray", "Check panel uniformity, clouding & banding"),
        ("#FFFF00", "Pure Yellow", "Subpixel blend verification (Red + Green)"),
        ("#00FFFF", "Pure Cyan", "Subpixel blend verification (Green + Blue)"),
        ("#FF00FF", "Pure Magenta", "Subpixel blend verification (Red + Blue)")
    ]

    def __init__(self, parent: Optional[tk.Tk] = None):
        self.parent = parent
        self.current_idx = 0
        self.show_grid = False
        self.hud_visible = True

        # Create window
        if self.parent:
            self.top = tk.Toplevel(self.parent)
        else:
            self.top = tk.Tk()

        self.top.title("TrueSpec - LCD Dead Pixel Inspector")
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.configure(background=self.COLOR_PALETTE[0][0], cursor="arrow")

        # Get screen dimensions
        self.screen_w = self.top.winfo_screenwidth()
        self.screen_h = self.top.winfo_screenheight()

        # Canvas fills the entire screen
        self.canvas = tk.Canvas(
            self.top,
            width=self.screen_w,
            height=self.screen_h,
            highlightthickness=0,
            cursor="arrow"
        )
        self.canvas.pack(fill="both", expand=True)

        # Draw initial screen
        self._render_screen()

        # Register universal keyboard & mouse bindings
        self._setup_event_bindings()

        # Ensure immediate window focus so keys work instantaneously
        self.top.lift()
        self.top.focus_force()
        self.canvas.focus_set()
        try:
            self.top.grab_set()
        except Exception:
            pass

    def _setup_event_bindings(self):
        """Registers keyboard and mouse events across both window and canvas."""
        # Keyboard actions
        exit_keys = ["<Escape>", "q", "Q", "x", "X"]
        next_keys = ["<space>", "<Right>", "<Down>", "<Return>", "n", "N"]
        prev_keys = ["<Left>", "<Up>", "<BackSpace>", "p", "P"]
        grid_keys = ["g", "G"]
        hud_keys = ["h", "H"]

        for k in exit_keys:
            self.top.bind(k, self._on_exit)
            self.canvas.bind(k, self._on_exit)

        for k in next_keys:
            self.top.bind(k, self._on_next)
            self.canvas.bind(k, self._on_next)

        for k in prev_keys:
            self.top.bind(k, self._on_prev)
            self.canvas.bind(k, self._on_prev)

        for k in grid_keys:
            self.top.bind(k, self._toggle_grid)
            self.canvas.bind(k, self._toggle_grid)

        for k in hud_keys:
            self.top.bind(k, self._toggle_hud)
            self.canvas.bind(k, self._toggle_hud)

        # Mouse clicks on canvas
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Button-3>", self._on_exit)          # Right-click always exits!
        self.canvas.bind("<Double-Button-1>", self._on_exit)   # Double-click always exits!

    def _render_screen(self):
        """Clears canvas and renders the background color, grid, and HUD."""
        self.canvas.delete("all")
        color_hex, color_name, color_desc = self.COLOR_PALETTE[self.current_idx]
        self.canvas.configure(bg=color_hex)

        # 1. Draw alignment grid if enabled
        if self.show_grid:
            self._draw_alignment_grid(color_hex)

        # 2. Always draw top-right prominent EXIT button
        self._draw_top_exit_button()

        # 3. Draw bottom navigation HUD if enabled
        if self.hud_visible:
            self._draw_bottom_hud(color_hex, color_name, color_desc)

    def _draw_alignment_grid(self, current_bg: str):
        """Draws a fine 64px grid across the screen to pinpoint pixel coordinates."""
        grid_color = "#333333" if current_bg in ("#FFFFFF", "#FFFF00", "#00FFFF", "#808080") else "#CCCCCC"
        step = 64
        for x in range(0, self.screen_w, step):
            self.canvas.create_line(x, 0, x, self.screen_h, fill=grid_color, width=1, dash=(2, 4), tags="grid")
        for y in range(0, self.screen_h, step):
            self.canvas.create_line(0, y, self.screen_w, y, fill=grid_color, width=1, dash=(2, 4), tags="grid")

    def _draw_top_exit_button(self):
        """Draws a prominent, high-contrast red '✕ Exit Test (Esc)' button at top-right."""
        bx2 = self.screen_w - 24
        bx1 = bx2 - 170
        by1 = 20
        by2 = by1 + 44

        # Red button background
        self.canvas.create_rectangle(
            bx1, by1, bx2, by2,
            fill="#DC2626",
            outline="#EF4444",
            width=2,
            tags="btn_exit"
        )
        self.canvas.create_text(
            (bx1 + bx2) // 2, (by1 + by2) // 2,
            text="✕ EXIT TEST (ESC)",
            font=("Segoe UI", 11, "bold"),
            fill="#FFFFFF",
            tags="btn_exit"
        )

        # Make button tag clickable
        self.canvas.tag_bind("btn_exit", "<Button-1>", self._on_exit)

    def _draw_bottom_hud(self, color_hex: str, color_name: str, color_desc: str):
        """Draws an informative navigation bar at the bottom with quick jump color dots."""
        is_light = color_hex in ("#FFFFFF", "#FFFF00", "#00FFFF", "#808080")
        hud_bg = "#0F172A" if is_light else "#1E293B"
        hud_fg = "#F8FAFC" if is_light else "#F1F5F9"
        hud_sub = "#94A3B8" if is_light else "#CBD5E1"
        border_col = "#334155" if is_light else "#475569"

        pw = min(880, self.screen_w - 60)
        ph = 76
        x1 = (self.screen_w - pw) // 2
        y1 = self.screen_h - ph - 24
        x2 = x1 + pw
        y2 = y1 + ph

        # Outer card box
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=hud_bg,
            outline=border_col,
            width=2,
            tags="hud"
        )

        # Prev Button (◀ Prev)
        prev_x1, prev_x2 = x1 + 16, x1 + 110
        btn_y1, btn_y2 = y1 + 18, y2 - 18
        self.canvas.create_rectangle(
            prev_x1, btn_y1, prev_x2, btn_y2,
            fill="#334155",
            outline="#475569",
            width=1,
            tags=("hud", "btn_prev")
        )
        self.canvas.create_text(
            (prev_x1 + prev_x2) // 2, (btn_y1 + btn_y2) // 2,
            text="◀ PREV",
            font=("Segoe UI", 10, "bold"),
            fill="#FFFFFF",
            tags=("hud", "btn_prev")
        )
        self.canvas.tag_bind("btn_prev", "<Button-1>", self._on_prev)

        # Next Button (Next ▶)
        next_x1, next_x2 = x2 - 110, x2 - 16
        self.canvas.create_rectangle(
            next_x1, btn_y1, next_x2, btn_y2,
            fill="#2563EB",
            outline="#3B82F6",
            width=1,
            tags=("hud", "btn_next")
        )
        self.canvas.create_text(
            (next_x1 + next_x2) // 2, (btn_y1 + btn_y2) // 2,
            text="NEXT ▶",
            font=("Segoe UI", 10, "bold"),
            fill="#FFFFFF",
            tags=("hud", "btn_next")
        )
        self.canvas.tag_bind("btn_next", "<Button-1>", self._on_next)

        # Grid Toggle Button
        grid_x1, grid_x2 = next_x1 - 120, next_x1 - 10
        grid_bg = "#059669" if self.show_grid else "#1E293B"
        grid_txt = "GRID: ON" if self.show_grid else "GRID: OFF"
        self.canvas.create_rectangle(
            grid_x1, btn_y1, grid_x2, btn_y2,
            fill=grid_bg,
            outline="#475569",
            width=1,
            tags=("hud", "btn_grid")
        )
        self.canvas.create_text(
            (grid_x1 + grid_x2) // 2, (btn_y1 + btn_y2) // 2,
            text=f"▦ {grid_txt}",
            font=("Segoe UI", 9, "bold"),
            fill="#FFFFFF",
            tags=("hud", "btn_grid")
        )
        self.canvas.tag_bind("btn_grid", "<Button-1>", self._toggle_grid)

        # Center Status Text
        center_x = (prev_x2 + grid_x1) // 2
        self.canvas.create_text(
            center_x, y1 + 24,
            text=f"Screen Pattern [{self.current_idx + 1}/{len(self.COLOR_PALETTE)}]: {color_name}",
            font=("Segoe UI", 12, "bold"),
            fill=hud_fg,
            tags="hud"
        )
        self.canvas.create_text(
            center_x, y1 + 50,
            text=f"{color_desc}  •  [Right-Click / ESC to Exit]",
            font=("Segoe UI", 10),
            fill=hud_sub,
            tags="hud"
        )

    def _on_canvas_click(self, event):
        """Clicking on the background cycles to next color; ignores clicks on HUD elements."""
        tags = self.canvas.gettags(self.canvas.find_withtag("current"))
        if "btn_exit" in tags or "btn_prev" in tags or "btn_next" in tags or "btn_grid" in tags or "hud" in tags:
            return  # Handled by specific tag bindings
        self._on_next()

    def _on_next(self, event=None):
        self.current_idx = (self.current_idx + 1) % len(self.COLOR_PALETTE)
        self._render_screen()

    def _on_prev(self, event=None):
        self.current_idx = (self.current_idx - 1) % len(self.COLOR_PALETTE)
        self._render_screen()

    def _toggle_grid(self, event=None):
        self.show_grid = not self.show_grid
        self._render_screen()

    def _toggle_hud(self, event=None):
        self.hud_visible = not self.hud_visible
        self._render_screen()

    def _on_exit(self, event=None):
        """Gracefully tears down the fullscreen window and releases grab."""
        try:
            self.top.grab_release()
        except Exception:
            pass
        self.top.destroy()
        if not self.parent:
            sys.exit(0)


def launch_screen_test(parent=None):
    """Entry point to launch the dead pixel tester."""
    app = DeadPixelTester(parent=parent)
    if not parent:
        app.top.mainloop()
    return app


if __name__ == "__main__":
    launch_screen_test()
