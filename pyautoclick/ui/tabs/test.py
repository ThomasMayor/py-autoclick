"""Test tab: live mouse event display."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.ui.tabs.base import BaseTab


class TestTab(BaseTab):
    title_key = "tab_test"

    def build(self) -> None:
        t = self.t
        SL = self.sticky_label
        L, C = self.col(0), self.col(1)
        justify = "right" if self.is_rtl else "left"

        ttk.Label(
            self, text=t("test_intro"), anchor=self.anchor_label, foreground="gray", justify=justify
        ).pack(
            anchor=self.anchor_label,
            pady=(0, 14),
        )

        box = ttk.LabelFrame(self, text=t("test_box_title"), padding=16)
        box.pack(fill="x")

        self.button_var = tk.StringVar(value="—")
        self.state_var = tk.StringVar(value="—")
        self.pos_var = tk.StringVar(value="—")
        self.cursor_var = tk.StringVar(value="—")

        def labeled(parent, r, label_key, var):
            ttk.Label(parent, text=t(label_key), anchor=self.anchor_label).grid(
                row=r,
                column=L,
                sticky=SL,
                pady=4,
            )
            ttk.Label(parent, textvariable=var, font=("monospace", 10, "bold")).grid(
                row=r,
                column=C,
                sticky=SL,
                padx=14,
            )

        labeled(box, 0, "label_button", self.button_var)
        labeled(box, 1, "label_state", self.state_var)
        labeled(box, 2, "label_clickpos", self.pos_var)
        labeled(box, 3, "label_curpos", self.cursor_var)

    # Called by App._on_button_seen (already marshaled to UI thread)
    def update_event(self, x: int, y: int, button, pressed: bool) -> None:
        try:
            self.button_var.set(str(button))
            self.state_var.set(self.t("state_pressed") if pressed else self.t("state_released"))
            self.pos_var.set(f"({x}, {y})")
        except (tk.TclError, AttributeError):
            pass

    # Called by App._tick
    def update_cursor(self, x: int, y: int) -> None:
        try:
            self.cursor_var.set(f"({x}, {y})")
        except (tk.TclError, AttributeError):
            pass
