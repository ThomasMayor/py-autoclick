"""Settings tab: language picker + system notification toggle.

These were originally crammed into the Shortcuts tab; moving them to a
dedicated tab gives the Shortcuts tab back its focus on hotkeys, and gives
the Settings tab room to grow as new app-wide preferences are added.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.i18n import LANG_LABELS, LANGUAGES
from pyautoclick.ui.tabs.base import BaseTab
from pyautoclick.ui.widgets.tooltip import Tooltip


class SettingsTab(BaseTab):
    title_key = "tab_settings"

    def build(self) -> None:
        self.columnconfigure(self.col(1), weight=1)
        t = self.t
        L, C = self.col(0), self.col(1)
        SL = self.sticky_label

        # Language selector
        ttk.Label(self, text=t("label_language"), anchor=self.anchor_label).grid(
            row=0,
            column=L,
            sticky=SL,
            pady=8,
        )
        lang_labels = [LANG_LABELS[c] for c in LANGUAGES]
        self.lang_var = tk.StringVar(value=LANG_LABELS[self.settings.language])
        cb_lang = ttk.Combobox(
            self,
            textvariable=self.lang_var,
            values=lang_labels,
            state="readonly",
        )
        cb_lang.grid(row=0, column=C, sticky="ew", pady=8)
        cb_lang.bind("<<ComboboxSelected>>", self._on_lang_change)
        Tooltip(cb_lang, t("language_tip"))

        # Notifications toggle
        self.notify_var = tk.BooleanVar(value=self.settings.notify_enabled)
        cbn = ttk.Checkbutton(
            self,
            text=t("notify_enable"),
            variable=self.notify_var,
            command=self._on_notify_change,
        )
        cbn.grid(row=1, column=0, columnspan=2, sticky=SL, pady=(12, 0))
        Tooltip(cbn, t("notify_tip"))

    # -------- Callbacks --------

    def _on_lang_change(self, _e) -> None:
        for code, lbl in LANG_LABELS.items():
            if lbl == self.lang_var.get():
                self.ctx.change_language(code)
                return

    def _on_notify_change(self) -> None:
        self.settings.notify_enabled = bool(self.notify_var.get())
        self.commit()
