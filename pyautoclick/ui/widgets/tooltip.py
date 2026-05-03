"""Borderless Toplevel tooltip."""

from __future__ import annotations

import tkinter as tk

from pyautoclick.ui.colors import TOOLTIP_BG, TOOLTIP_FG
from pyautoclick.ui.constants import (
    TOOLTIP_DELAY_MS,
    TOOLTIP_OFFSET,
    TOOLTIP_PADX,
    TOOLTIP_PADY,
)


class Tooltip:
    """Show ``text`` near ``widget`` after a hover delay."""

    def __init__(self, widget, text: str, delay: int = TOOLTIP_DELAY_MS):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip: tk.Toplevel | None = None
        self._after = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        self._cancel()
        self._after = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None

    def _show(self):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + TOOLTIP_OFFSET[0]
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + TOOLTIP_OFFSET[1]
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background=TOOLTIP_BG,
            foreground=TOOLTIP_FG,
            relief="solid",
            borderwidth=1,
            font=("", 9),
            padx=TOOLTIP_PADX,
            pady=TOOLTIP_PADY,
        )
        lbl.pack()

    def _hide(self, _e=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None
