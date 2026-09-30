"""
TrueSpec: Second-Hand Laptop Inspector
Module: screen_keyboard_test.py
Author: TrueSpec Core Systems Team

Interactive full-screen dead pixel and backlight bleed tester.
Cycles through solid primary and secondary colors on click/spacebar.
Press ESC or right-click to exit.
"""

import sys
import tkinter as tk
from typing import Optional


class DeadPixelTester:
    """
    Launches a borderless full-screen window cycling through test patterns:
    - Red, Green, Blue (primary subpixels)
    - White, Black (stuck pixels & backlight bleed / IPS glow)
    - 50% Gray (uniformity & banding)
    - Yellow, Cyan, Magenta (secondary subpixel faults)
    """

    COLOR_PALETTE = [
        ("#FF0000", "Pure Red (Check Red Subpixels)"),
        ("#00FF00", "Pure Green (Check Green Subpixels)"),
        ("#0000FF", "Pure Blue (Check Blue Subpixels)"),
        ("#FFFFFF", "Pure White (Check Dead Dark Pixels & Dust)"),
        ("#000000", "Pure Black (Check Backlight Bleed & Bright Stuck Pixels)"),
        ("#808080", "50% Uniform Gray (Check Panel Uniformity & Banding)"),
        ("#FFFF00", "Yellow (Subpixel Analysis)"),
        ("#00FFFF", "Cyan (Subpixel Analysis)"),
        ("#FF00FF", "Magenta (Subpixel Analysis)")
    ]

    def __init__(self, parent: Optional[tk.Tk] = None):
        self.parent = parent
        self.current_idx = 0

        # Create window
        if self.parent:
            self.top = tk.Toplevel(self.parent)
        else:
            self.top = tk.Tk()

        self.top.title("TrueSpec - Dead Pixel & Display Inspector")
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.configure(background=self.COLOR_PALETTE[0][0], cursor="none")

        # Canvas for color display and hint overlay
        self.canvas = tk.Canvas(self.top, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Draw initial background
        self._update_color()

        # Bindings
        self.top.bind("<Button-1>", self._on_next)
        self.top.bind("<space>", self._on_next)
        self.top.bind("<Right>", self._on_next)
        self.top.bind("<Return>", self._on_next)
        self.top.bind("<Left>", self._on_prev)
        self.top.bind("<Button-3>", self._on_exit)  # Right click to exit
        self.top.bind("<Escape>", self._on_exit)
        self.top.bind("q", self._on_exit)
        self.top.bind("Q", self._on_exit)

        # Show initial instruction badge for 3.5 seconds
        self.show_overlay = True
        self._draw_overlay()
        self.top.after(3500, self._fade_overlay)

    def _update_color(self):
        color_hex, label = self.COLOR_PALETTE[self.current_idx]
        self.canvas.configure(bg=color_hex)
        if self.show_overlay:
            self._draw_overlay()

    def _draw_overlay(self):
        self.canvas.delete("overlay")
        w = self.top.winfo_screenwidth()
        h = self.top.winfo_screenheight()

        color_hex, label = self.COLOR_PALETTE[self.current_idx]
        # Dark pill on light colors, light pill on dark colors
        is_light = color_hex in ("#FFFFFF", "#FFFF00", "#00FFFF", "#808080")
        pill_bg = "#111827" if is_light else "#F3F4F6"
        pill_fg = "#F9FAFB" if is_light else "#111827"
        sub_fg = "#9CA3AF" if is_light else "#4B5563"

        pw, ph = 640, 70
        x1 = (w - pw) // 2
        y1 = h - 110
        x2 = x1 + pw
        y2 = y1 + ph

        # Draw rounded rectangle background
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=pill_bg,
            outline="#374151" if is_light else "#D1D5DB",
            width=2,
            tags="overlay"
        )
        self.canvas.create_text(
            w // 2, y1 + 22,
            text=f"Screen Test [{self.current_idx + 1}/{len(self.COLOR_PALETTE)}]: {label}",
            font=("Segoe UI", 12, "bold"),
            fill=pill_fg,
            tags="overlay"
        )
        self.canvas.create_text(
            w // 2, y1 + 48,
            text="Click / Spacebar to cycle  •  Left Arrow to go back  •  ESC to exit",
            font=("Segoe UI", 10),
            fill=sub_fg,
            tags="overlay"
        )

    def _fade_overlay(self):
        self.show_overlay = False
        self.canvas.delete("overlay")

    def _on_next(self, event=None):
        self._fade_overlay()
        self.current_idx = (self.current_idx + 1) % len(self.COLOR_PALETTE)
        self._update_color()

    def _on_prev(self, event=None):
        self._fade_overlay()
        self.current_idx = (self.current_idx - 1) % len(self.COLOR_PALETTE)
        self._update_color()

    def _on_exit(self, event=None):
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
