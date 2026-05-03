"""Hold mode tab: trigger button + action + cps + jitter."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.core.buttons import (
    ACTION_BUTTONS,
    ACTION_KEYS,
    TRIGGER_BUTTONS,
    TRIGGER_KEYS,
)
from pyautoclick.ui.tabs.base import BaseTab
from pyautoclick.ui.widgets.tooltip import Tooltip


class HoldTab(BaseTab):
    title_key = "tab_hold"

    def build(self) -> None:
        # Control column expands; label column stays compact
        self.columnconfigure(self.col(1), weight=1)
        s, t = self.settings, self.t
        L, C = self.col(0), self.col(1)
        SL = self.sticky_label

        # Enable
        self.hold_enabled_var = tk.BooleanVar(value=s.hold_enabled)
        cbe = ttk.Checkbutton(
            self,
            text=t("hold_enable"),
            variable=self.hold_enabled_var,
            command=self._on_hold_toggle,
        )
        cbe.grid(row=0, column=0, columnspan=2, sticky=SL, pady=(0, 12))
        Tooltip(cbe, t("hold_enable_tip"))

        # Trigger
        ttk.Label(self, text=t("label_trigger"), anchor=self.anchor_label).grid(
            row=1,
            column=L,
            sticky=SL,
            pady=8,
        )
        trigger_labels = [t(f"trigger_{k}") for k in TRIGGER_KEYS]
        self.trigger_var = tk.StringVar(value=t(f"trigger_{s.trigger}"))
        cb = ttk.Combobox(
            self, textvariable=self.trigger_var, values=trigger_labels, state="readonly"
        )
        cb.grid(row=1, column=C, sticky="ew", pady=8)
        cb.bind("<<ComboboxSelected>>", self._on_trigger_change)
        Tooltip(cb, t("trigger_tip"))

        # Action
        ttk.Label(self, text=t("label_action"), anchor=self.anchor_label).grid(
            row=2,
            column=L,
            sticky=SL,
            pady=8,
        )
        action_labels = [t(f"action_{k}") for k in ACTION_KEYS]
        self.action_var = tk.StringVar(value=t(f"action_{s.action}"))
        cb2 = ttk.Combobox(
            self, textvariable=self.action_var, values=action_labels, state="readonly"
        )
        cb2.grid(row=2, column=C, sticky="ew", pady=8)
        cb2.bind("<<ComboboxSelected>>", self._on_action_change)
        Tooltip(cb2, t("action_tip"))

        # CPS (slider 1-50 + spinbox 1-200)
        ttk.Label(self, text=t("label_cps"), anchor=self.anchor_label).grid(
            row=3,
            column=L,
            sticky=SL,
            pady=8,
        )
        cps_frame = ttk.Frame(self)
        cps_frame.grid(row=3, column=C, sticky="ew", pady=8)
        self.cps_var = tk.IntVar(value=s.cps)
        sp_cps = ttk.Spinbox(
            cps_frame,
            from_=1,
            to=200,
            width=5,
            textvariable=self.cps_var,
            command=self._on_cps_spin,
        )
        sp_cps.pack(side=self.side("right"), padx=(6, 0))
        sp_cps.bind("<FocusOut>", lambda _e: self._on_cps_spin())
        sp_cps.bind("<Return>", lambda _e: self._on_cps_spin())
        scale = ttk.Scale(
            cps_frame, from_=1, to=50, orient="horizontal", command=self._on_cps_scale
        )
        scale.set(min(50, s.cps))
        scale.pack(side=self.side("left"), fill="x", expand=True)
        self._cps_scale = scale
        Tooltip(sp_cps, t("cps_tip"))

        # Jitter
        ttk.Label(self, text=t("label_jitter"), anchor=self.anchor_label).grid(
            row=4,
            column=L,
            sticky=SL,
            pady=8,
        )
        self.hold_jitter_var = tk.IntVar(value=s.hold_jitter_ms)
        sp_j = ttk.Spinbox(
            self,
            from_=0,
            to=500,
            increment=5,
            textvariable=self.hold_jitter_var,
            command=self._on_hold_jitter,
        )
        sp_j.grid(row=4, column=C, sticky="ew", pady=8)
        sp_j.bind("<FocusOut>", lambda _e: self._on_hold_jitter())
        sp_j.bind("<Return>", lambda _e: self._on_hold_jitter())
        Tooltip(sp_j, t("hold_jitter_tip"))

    # -------- Callbacks --------

    def _on_hold_toggle(self):
        v = self.hold_enabled_var.get()
        self.clicker.set_hold_enabled(v)
        self.settings.hold_enabled = v
        self.commit()

    def _on_trigger_change(self, _e):
        for k in TRIGGER_KEYS:
            if self.t(f"trigger_{k}") == self.trigger_var.get():
                self.settings.trigger = k
                self.clicker.set_trigger(TRIGGER_BUTTONS[k])
                self.commit()
                return

    def _on_action_change(self, _e):
        for k in ACTION_KEYS:
            if self.t(f"action_{k}") == self.action_var.get():
                self.settings.action = k
                self.clicker.set_click_btn(ACTION_BUTTONS[k])
                self.commit()
                return

    def _on_cps_spin(self):
        try:
            v = max(1, min(200, int(self.cps_var.get())))
        except (tk.TclError, ValueError):
            v = self.settings.cps
            self.cps_var.set(v)
        self.clicker.set_cps(v)
        self.settings.cps = v
        if v <= 50:
            self._cps_scale.set(v)
        self.commit()

    def _on_cps_scale(self, value):
        v = int(float(value))
        self.cps_var.set(v)
        self.clicker.set_cps(v)
        self.settings.cps = v
        self.commit()

    def _on_hold_jitter(self):
        try:
            v = max(0, int(self.hold_jitter_var.get()))
        except (tk.TclError, ValueError):
            v = self.settings.hold_jitter_ms
            self.hold_jitter_var.set(v)
        self.clicker.set_hold_jitter_ms(v)
        self.settings.hold_jitter_ms = v
        self.commit()
