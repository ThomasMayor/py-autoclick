"""Positions tab: list of (x, y) cycled by auto mode."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.ui.constants import POSITION_CAPTURE_DELAY_MS, POSITIONS_LISTBOX_HEIGHT
from pyautoclick.ui.tabs.base import BaseTab
from pyautoclick.ui.theme import theme_listbox
from pyautoclick.ui.widgets.tooltip import Tooltip


class PositionsTab(BaseTab):
    title_key = "tab_positions"

    def build(self) -> None:
        # Listbox column expands; scrollbar column stays compact
        self.columnconfigure(self.col(0), weight=1)
        self.rowconfigure(1, weight=1)
        t = self.t
        SL = self.sticky_label

        ttk.Label(
            self, text=t("positions_intro"), anchor=self.anchor_label, foreground="gray"
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky=SL,
            pady=(0, 8),
        )

        self.pos_listbox = tk.Listbox(
            self,
            height=POSITIONS_LISTBOX_HEIGHT,
            activestyle="dotbox",
            borderwidth=0,
            highlightthickness=1,
            relief="flat",
            exportselection=False,
        )
        theme_listbox(self.pos_listbox, self.ctx.get_theme())
        self.pos_listbox.grid(row=1, column=self.col(0), sticky="nsew")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.pos_listbox.yview)
        sb.grid(row=1, column=self.col(1), sticky="ns")
        self.pos_listbox.config(yscrollcommand=sb.set)
        self._refresh()

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        # In RTL, we still pack from the same anchor side so the visual order
        # of buttons mirrors (Add | Add(3s) | Remove | Clear).
        side = self.side("left")
        b1 = ttk.Button(btns, text=t("btn_add"), command=self._add_current)
        b1.pack(side=side)
        Tooltip(b1, t("btn_add_tip"))
        b2 = ttk.Button(btns, text=t("btn_add_delayed"), command=self._add_delayed)
        b2.pack(side=side, padx=(6, 0))
        Tooltip(b2, t("btn_add_delayed_tip"))
        ttk.Button(btns, text=t("btn_remove"), command=self._remove).pack(side=side, padx=(6, 0))
        ttk.Button(btns, text=t("btn_clear"), command=self._clear).pack(side=side, padx=(6, 0))

    def _refresh(self) -> None:
        self.pos_listbox.delete(0, tk.END)
        for i, (x, y) in enumerate(self.clicker.positions, 1):
            self.pos_listbox.insert(tk.END, f"{i:3d}.  x={x}, y={y}")

    def _commit_positions(self) -> None:
        self.settings.auto_positions = self.clicker.positions
        self.commit()
        self._refresh()

    def _add_current(self) -> None:
        try:
            x, y = self.clicker.controller.position
            pos = (int(x), int(y))
        except (TypeError, ValueError):
            return
        self.clicker.add_position(pos)
        self._commit_positions()

    def _add_delayed(self) -> None:
        self.ctx.set_status(self.t("status_capture"))
        self.after(POSITION_CAPTURE_DELAY_MS, self._add_current)

    def _remove(self) -> None:
        sel = self.pos_listbox.curselection()
        if not sel:
            return
        self.clicker.remove_position(sel[0])
        self._commit_positions()

    def _clear(self) -> None:
        self.clicker.clear_positions()
        self._commit_positions()
