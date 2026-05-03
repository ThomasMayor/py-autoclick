"""Status bar at the bottom of the main window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.i18n import is_rtl
from pyautoclick.ui.colors import MUTED_GRAY
from pyautoclick.ui.constants import (
    STATUS_BAR_HOTKEY_GAP,
    STATUS_BAR_LABEL_GAP,
    STATUS_BAR_PADDING,
    THEME_BUTTON_WIDTH,
    THEME_DARK_GLYPH,
    THEME_LIGHT_GLYPH,
)
from pyautoclick.ui.context import AppContext
from pyautoclick.ui.widgets.tooltip import Tooltip


def _flip(side: str, rtl: bool) -> str:
    if not rtl:
        return side
    return {"left": "right", "right": "left"}.get(side, side)


class StatusBar(ttk.Frame):
    """Status (left) | Click count | Active hotkeys | Theme button (right)."""

    def __init__(self, parent, ctx: AppContext):
        super().__init__(parent, padding=STATUS_BAR_PADDING)
        self.ctx = ctx
        self._rtl = is_rtl(ctx.settings.language or "en")

        self.status_var = tk.StringVar(value=ctx.t("status_waiting"))
        self.count_var = tk.StringVar(value=ctx.t("label_clicks", n=0))
        self.hotkey_status_var = tk.StringVar(value="")

        # In RTL: status & count are anchored to the right edge, theme & hotkeys
        # to the left edge — i.e. all sides flipped.
        ttk.Label(self, textvariable=self.status_var,
                  font=("", 9, "bold")).pack(side=_flip("left", self._rtl))
        ttk.Label(self, textvariable=self.count_var).pack(
            side=_flip("left", self._rtl), padx=STATUS_BAR_LABEL_GAP,
        )

        self.theme_btn = ttk.Button(self, width=THEME_BUTTON_WIDTH,
                                    command=ctx.toggle_theme)
        self.theme_btn.pack(side=_flip("right", self._rtl))
        Tooltip(self.theme_btn, ctx.t("theme_tip"))
        self.update_theme_icon()

        ttk.Label(self, textvariable=self.hotkey_status_var,
                  foreground=MUTED_GRAY).pack(
            side=_flip("right", self._rtl), padx=(0, STATUS_BAR_HOTKEY_GAP),
        )

    def update_theme_icon(self) -> None:
        is_dark = self.ctx.get_theme() == "dark"
        self.theme_btn.config(text=THEME_DARK_GLYPH if is_dark else THEME_LIGHT_GLYPH)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def set_count(self, n: int) -> None:
        self.count_var.set(self.ctx.t("label_clicks", n=n))

    def set_hotkeys(self, combos: list[str]) -> None:
        if combos:
            self.hotkey_status_var.set(self.ctx.t("label_hotkeys", x=" | ".join(combos)))
        else:
            self.hotkey_status_var.set("")
