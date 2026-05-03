"""Read-only entry + Capture / Clear buttons for a single hotkey combo."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.ui.constants import HOTKEY_CLEAR_GLYPH
from pyautoclick.ui.widgets.capture_dialog import capture_hotkey_dialog


class HotkeyEntry(ttk.Frame):
    def __init__(self, parent, value: str, on_change, *, t_func):
        super().__init__(parent)
        self.var = tk.StringVar(value=value or "")
        self.on_change = on_change
        self.t = t_func

        self.entry = ttk.Entry(self, textvariable=self.var, state="readonly")
        self.entry.pack(side="left", fill="x", expand=True)
        ttk.Button(self, text=t_func("btn_capture"),
                   command=self._capture).pack(side="left", padx=(4, 0))
        ttk.Button(self, text=HOTKEY_CLEAR_GLYPH,
                   command=self._clear).pack(side="left", padx=(4, 0))

    def _capture(self):
        capture_hotkey_dialog(
            self.winfo_toplevel(), self._on_captured,
            title=self.t("capture_title"),
            prompt=self.t("capture_prompt"),
            in_progress_tpl=self.t("capture_inprogress"),
            unknown_tpl=self.t("capture_unknown"),
        )

    def _on_captured(self, combo):
        if combo is None:
            return
        self.var.set(combo)
        self.on_change(combo)

    def _clear(self):
        self.var.set("")
        self.on_change("")
