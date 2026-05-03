"""Hotkeys tab: 3 hotkeys + notification toggle + language selector."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.i18n import LANG_LABELS, LANGUAGES
from pyautoclick.ui.colors import ERROR_RED, WARNING_AMBER
from pyautoclick.ui.tabs.base import BaseTab
from pyautoclick.ui.widgets.hotkey_entry import HotkeyEntry
from pyautoclick.ui.widgets.tooltip import Tooltip

# Map platform_capabilities caveat code -> i18n key
_CAVEAT_KEYS = {
    "wayland_hotkeys_blocked": "caveat_wayland_hotkeys",
    "wayland_mouse_xwayland_only": "caveat_wayland_hotkeys",  # same message covers both
    "macos_accessibility_required": "caveat_macos_accessibility",
    "unknown_display_server": "caveat_unknown_display",
    "unknown_os": "caveat_unknown_display",
}


class HotkeysTab(BaseTab):
    title_key = "tab_hotkeys"

    def build(self) -> None:
        self.columnconfigure(self.col(1), weight=1)
        t = self.t
        L, C = self.col(0), self.col(1)
        SL = self.sticky_label

        # Platform capability warning at the very top
        row_off = self._build_caveat_banner()

        def hk_row(r, label_key, cfg_attr, tip_key):
            ttk.Label(self, text=t(label_key), anchor=self.anchor_label).grid(
                row=r,
                column=L,
                sticky=SL,
                pady=8,
            )
            entry = HotkeyEntry(
                self,
                getattr(self.settings, cfg_attr),
                lambda combo, k=cfg_attr: self._on_hotkey_change(k, combo),
                t_func=t,
            )
            entry.grid(row=r, column=C, sticky="ew", pady=8)
            Tooltip(entry.entry, t(tip_key))

        hk_row(row_off + 0, "hk_toggle", "hotkey_auto_toggle", "hk_toggle_tip")
        hk_row(row_off + 1, "hk_momentary", "hotkey_auto_momentary", "hk_momentary_tip")
        hk_row(row_off + 2, "hk_panic", "hotkey_panic", "hk_panic_tip")

        ttk.Separator(self).grid(row=row_off + 3, column=0, columnspan=2, sticky="ew", pady=16)

        # Notifications
        self.notify_var = tk.BooleanVar(value=self.settings.notify_enabled)
        cbn = ttk.Checkbutton(
            self, text=t("notify_enable"), variable=self.notify_var, command=self._on_notify_change
        )
        cbn.grid(row=row_off + 4, column=0, columnspan=2, sticky=SL, pady=(0, 8))
        Tooltip(cbn, t("notify_tip"))

        # Language selector
        ttk.Label(self, text=t("label_language"), anchor=self.anchor_label).grid(
            row=row_off + 5,
            column=L,
            sticky=SL,
            pady=8,
        )
        lang_labels = [LANG_LABELS[c] for c in LANGUAGES]
        self.lang_var = tk.StringVar(value=LANG_LABELS[self.settings.language])
        cb_lang = ttk.Combobox(
            self, textvariable=self.lang_var, values=lang_labels, state="readonly"
        )
        cb_lang.grid(row=row_off + 5, column=C, sticky="ew", pady=8)
        cb_lang.bind("<<ComboboxSelected>>", self._on_lang_change)
        Tooltip(cb_lang, t("language_tip"))

        # Invalid combos error label
        self.error_var = tk.StringVar(value="")
        ttk.Label(
            self, textvariable=self.error_var, anchor=self.anchor_label, foreground=ERROR_RED
        ).grid(row=row_off + 6, column=0, columnspan=2, sticky=SL, pady=(8, 0))

    def _build_caveat_banner(self) -> int:
        """If the platform has known limitations, render an amber warning.

        Returns the row offset for subsequent widgets (0 if no banner, 1 if banner).
        """
        caps = self.ctx.capabilities
        if not caps.caveats:
            return 0
        # Deduplicate translation keys so we don't show "Wayland..." twice
        seen: list[str] = []
        for code in caps.caveats:
            key = _CAVEAT_KEYS.get(code)
            if key and key not in seen:
                seen.append(key)
        if not seen:
            return 0
        text = "\n".join(self.t(k) for k in seen)
        justify = "right" if self.is_rtl else "left"
        ttk.Label(
            self,
            text="⚠ " + text,
            foreground=WARNING_AMBER,
            wraplength=560,
            justify=justify,
            anchor=self.anchor_label,
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 12),
        )
        return 1

    # -------- Callbacks --------

    def _on_hotkey_change(self, key: str, combo: str) -> None:
        setattr(self.settings, key, combo)
        self.commit()
        self.ctx.refresh_hotkeys()

    def _on_notify_change(self) -> None:
        self.settings.notify_enabled = bool(self.notify_var.get())
        self.commit()

    def _on_lang_change(self, _e) -> None:
        for code, lbl in LANG_LABELS.items():
            if lbl == self.lang_var.get():
                self.ctx.change_language(code)
                return

    # Called by App after (re)configuring the HotkeyManager
    def set_error(self, text: str) -> None:
        self.error_var.set(text)
