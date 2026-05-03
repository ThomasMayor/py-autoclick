"""Auto mode tab: action + interval + press duration + jitter + limit + positions toggle."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.core.buttons import ACTION_BUTTONS, ACTION_KEYS
from pyautoclick.ui.tabs.base import BaseTab
from pyautoclick.ui.widgets.tooltip import Tooltip


class AutoTab(BaseTab):
    title_key = "tab_auto"

    def build(self) -> None:
        self.columnconfigure(self.col(1), weight=1)
        s, t = self.settings, self.t
        L, C = self.col(0), self.col(1)
        SL = self.sticky_label

        # Enable
        self.auto_var = tk.BooleanVar(value=False)
        cbx = ttk.Checkbutton(
            self, text=t("auto_enable"), variable=self.auto_var, command=self._on_auto_toggle
        )
        cbx.grid(row=0, column=0, columnspan=2, sticky=SL, pady=(0, 12))
        Tooltip(cbx, t("auto_enable_tip"))

        # Action
        ttk.Label(self, text=t("label_action"), anchor=self.anchor_label).grid(
            row=1,
            column=L,
            sticky=SL,
            pady=8,
        )
        action_labels = [t(f"action_{k}") for k in ACTION_KEYS]
        self.auto_action_var = tk.StringVar(value=t(f"action_{s.auto_action}"))
        cb = ttk.Combobox(
            self, textvariable=self.auto_action_var, values=action_labels, state="readonly"
        )
        cb.grid(row=1, column=C, sticky="ew", pady=8)
        cb.bind("<<ComboboxSelected>>", self._on_auto_action_change)

        # Interval
        ttk.Label(self, text=t("label_interval"), anchor=self.anchor_label).grid(
            row=2,
            column=L,
            sticky=SL,
            pady=8,
        )
        self.auto_interval_var = tk.IntVar(value=s.auto_interval_ms)
        sp1 = ttk.Spinbox(
            self,
            from_=1,
            to=10000,
            increment=10,
            textvariable=self.auto_interval_var,
            command=self._on_interval_change,
        )
        sp1.grid(row=2, column=C, sticky="ew", pady=8)
        sp1.bind("<FocusOut>", lambda _e: self._on_interval_change())
        sp1.bind("<Return>", lambda _e: self._on_interval_change())
        Tooltip(sp1, t("interval_tip"))

        # Press duration
        ttk.Label(self, text=t("label_press"), anchor=self.anchor_label).grid(
            row=3,
            column=L,
            sticky=SL,
            pady=8,
        )
        self.auto_press_var = tk.IntVar(value=s.auto_press_ms)
        sp2 = ttk.Spinbox(
            self,
            from_=0,
            to=2000,
            increment=5,
            textvariable=self.auto_press_var,
            command=self._on_press_change,
        )
        sp2.grid(row=3, column=C, sticky="ew", pady=8)
        sp2.bind("<FocusOut>", lambda _e: self._on_press_change())
        sp2.bind("<Return>", lambda _e: self._on_press_change())
        Tooltip(sp2, t("press_tip"))

        # Jitter
        ttk.Label(self, text=t("label_jitter"), anchor=self.anchor_label).grid(
            row=4,
            column=L,
            sticky=SL,
            pady=8,
        )
        self.auto_jitter_var = tk.IntVar(value=s.auto_jitter_ms)
        sp3 = ttk.Spinbox(
            self,
            from_=0,
            to=2000,
            increment=5,
            textvariable=self.auto_jitter_var,
            command=self._on_jitter_change,
        )
        sp3.grid(row=4, column=C, sticky="ew", pady=8)
        sp3.bind("<FocusOut>", lambda _e: self._on_jitter_change())
        sp3.bind("<Return>", lambda _e: self._on_jitter_change())
        Tooltip(sp3, t("auto_jitter_tip"))

        # Click limit
        ttk.Label(self, text=t("label_limit"), anchor=self.anchor_label).grid(
            row=5,
            column=L,
            sticky=SL,
            pady=8,
        )
        self.auto_limit_var = tk.IntVar(value=s.auto_click_limit)
        sp4 = ttk.Spinbox(
            self,
            from_=0,
            to=1_000_000,
            increment=10,
            textvariable=self.auto_limit_var,
            command=self._on_limit_change,
        )
        sp4.grid(row=5, column=C, sticky="ew", pady=8)
        sp4.bind("<FocusOut>", lambda _e: self._on_limit_change())
        sp4.bind("<Return>", lambda _e: self._on_limit_change())
        Tooltip(sp4, t("limit_tip"))

        # Cycle through positions
        self.use_positions_var = tk.BooleanVar(value=s.auto_use_positions)
        cbp = ttk.Checkbutton(
            self,
            text=t("use_positions"),
            variable=self.use_positions_var,
            command=self._on_use_positions_change,
        )
        cbp.grid(row=6, column=0, columnspan=2, sticky=SL, pady=(12, 0))
        Tooltip(cbp, t("use_positions_tip"))

    # -------- Callbacks --------

    def _on_auto_toggle(self):
        v = self.auto_var.get()
        self.clicker.set_auto(v)
        if v:
            self.ctx.notify(self.t("app_title"), self.t("notif_auto_started"))

    def _on_auto_action_change(self, _e):
        for k in ACTION_KEYS:
            if self.t(f"action_{k}") == self.auto_action_var.get():
                self.settings.auto_action = k
                self.clicker.set_auto_btn(ACTION_BUTTONS[k])
                self.commit()
                return

    def _on_interval_change(self):
        try:
            v = max(1, int(self.auto_interval_var.get()))
        except (tk.TclError, ValueError):
            v = self.settings.auto_interval_ms
            self.auto_interval_var.set(v)
        self.clicker.set_auto_interval_ms(v)
        self.settings.auto_interval_ms = v
        self.commit()

    def _on_press_change(self):
        try:
            v = max(0, int(self.auto_press_var.get()))
        except (tk.TclError, ValueError):
            v = self.settings.auto_press_ms
            self.auto_press_var.set(v)
        self.clicker.set_auto_press_ms(v)
        self.settings.auto_press_ms = v
        self.commit()

    def _on_jitter_change(self):
        try:
            v = max(0, int(self.auto_jitter_var.get()))
        except (tk.TclError, ValueError):
            v = self.settings.auto_jitter_ms
            self.auto_jitter_var.set(v)
        self.clicker.set_auto_jitter_ms(v)
        self.settings.auto_jitter_ms = v
        self.commit()

    def _on_limit_change(self):
        try:
            v = max(0, int(self.auto_limit_var.get()))
        except (tk.TclError, ValueError):
            v = self.settings.auto_click_limit
            self.auto_limit_var.set(v)
        self.clicker.set_auto_click_limit(v)
        self.settings.auto_click_limit = v
        self.commit()

    def _on_use_positions_change(self):
        v = self.use_positions_var.get()
        self.clicker.set_use_positions(v)
        self.settings.auto_use_positions = v
        self.commit()
