"""Main App orchestrator.

Owns: Tk root, AutoClicker, HotkeyManager, Settings, language. Composes
the UI from StatusBar + Notebook + tabs. Provides AppContext to all
children for two-way wiring (callbacks + shared state).
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from pyautoclick.core.buttons import ACTION_BUTTONS, TRIGGER_BUTTONS
from pyautoclick.core.clicker import AutoClicker
from pyautoclick.core.hotkeys import HotkeyManager
from pyautoclick.core.platform_capabilities import PlatformCapabilities, detect
from pyautoclick.core.single_instance import cleanup_socket
from pyautoclick.i18n import LANGUAGES, detect_system_language, t
from pyautoclick.persistence.settings import Settings
from pyautoclick.services.notifications import notify
from pyautoclick.ui.constants import (
    NOTEBOOK_PADX,
    NOTEBOOK_PADY_TOP,
    TICK_INTERVAL_MS,
    WINDOW_GEOMETRY,
    WINDOW_MIN_SIZE,
)
from pyautoclick.ui.context import (
    AppContext,
    LifecycleContext,
    ServicesContext,
    StateContext,
)
from pyautoclick.ui.status_bar import StatusBar
from pyautoclick.ui.tabs import ALL_TABS
from pyautoclick.ui.tabs.base import BaseTab
from pyautoclick.ui.tabs.hotkeys import HotkeysTab
from pyautoclick.ui.tabs.positions import PositionsTab
from pyautoclick.ui.tabs.test import TestTab
from pyautoclick.ui.theme import apply_theme, theme_listbox

logger = logging.getLogger(__name__)


class App:
    def __init__(self, root: tk.Tk, *, capabilities: PlatformCapabilities | None = None):
        self.root = root
        self.capabilities = capabilities or detect()
        self.settings = Settings.load()

        # Detect language at first launch
        if not self.settings.language or self.settings.language not in LANGUAGES:
            self.settings.language = detect_system_language()
        self.lang = self.settings.language

        # Persist cleaned settings + detected language
        self.settings.save()

        apply_theme(self.settings.theme)

        self.clicker = AutoClicker(
            on_button_seen=self._on_button_seen,
            on_auto_stopped=self._on_auto_stopped,
        )
        self._sync_clicker_from_settings()

        self.hotkey_manager = HotkeyManager()
        self.notebook: ttk.Notebook | None = None
        self.status_bar: StatusBar | None = None
        self.tabs: dict[str, BaseTab] = {}

        root.geometry(WINDOW_GEOMETRY)
        root.minsize(*WINDOW_MIN_SIZE)

        self._build_ui()
        self._refresh_hotkeys()

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick()

    # -------- Settings -> clicker push --------

    def _sync_clicker_from_settings(self) -> None:
        s = self.settings
        c = self.clicker
        c.set_hold_enabled(s.hold_enabled)
        c.set_trigger(TRIGGER_BUTTONS[s.trigger])
        c.set_click_btn(ACTION_BUTTONS[s.action])
        c.set_cps(s.cps)
        c.set_hold_jitter_ms(s.hold_jitter_ms)
        c.set_auto_btn(ACTION_BUTTONS[s.auto_action])
        c.set_auto_interval_ms(s.auto_interval_ms)
        c.set_auto_press_ms(s.auto_press_ms)
        c.set_auto_jitter_ms(s.auto_jitter_ms)
        c.set_auto_click_limit(s.auto_click_limit)
        c.set_use_positions(s.auto_use_positions)
        c.set_positions([tuple(p) for p in s.auto_positions])

    # -------- Translation helper --------

    def _t(self, key: str, **kwargs) -> str:
        return t(key, self.lang, **kwargs)

    # -------- AppContext factory --------

    def _make_context(self) -> AppContext:
        return AppContext(
            state=StateContext(
                settings=self.settings,
                clicker=self.clicker,
                commit=self.settings.save,
            ),
            services=ServicesContext(
                t=self._t,
                notify=self._maybe_notify,
                set_status=self._set_status,
            ),
            lifecycle=LifecycleContext(
                get_theme=lambda: self.settings.theme,
                toggle_theme=self._toggle_theme,
                change_language=self._change_language,
                refresh_hotkeys=self._refresh_hotkeys,
                capabilities=self.capabilities,
            ),
        )

    def _set_status(self, text: str) -> None:
        if self.status_bar:
            self.status_bar.set_status(text)

    def _maybe_notify(self, title: str, message: str) -> None:
        if self.settings.notify_enabled:
            notify(title, message)

    # -------- UI build / rebuild --------

    def _build_ui(self) -> None:
        self.root.title(self._t("app_title"))
        ctx = self._make_context()

        self.status_bar = StatusBar(self.root, ctx)
        self.status_bar.pack(side="bottom", fill="x")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(
            fill="both", expand=True, padx=NOTEBOOK_PADX, pady=(NOTEBOOK_PADY_TOP, 0)
        )

        self.tabs = {}
        for TabCls in ALL_TABS:
            tab = TabCls(self.notebook, ctx)
            self.notebook.add(tab, text=ctx.t(TabCls.title_key))
            self.tabs[TabCls.__name__] = tab

    def _rebuild_ui(self) -> None:
        try:
            current = self.notebook.index("current") if self.notebook else 0
        except tk.TclError:
            current = 0
        for w in list(self.root.winfo_children()):
            w.destroy()
        self._build_ui()
        try:
            self.notebook.select(current)
        except tk.TclError:
            pass
        self._refresh_hotkeys()

    # -------- Theme --------

    def _toggle_theme(self) -> None:
        new = "light" if self.settings.theme == "dark" else "dark"
        self.settings.theme = new
        self.settings.save()
        apply_theme(new)
        # Re-align non-ttk widgets (Listbox in PositionsTab)
        positions_tab = self.tabs.get("PositionsTab")
        if isinstance(positions_tab, PositionsTab):
            theme_listbox(positions_tab.pos_listbox, new)
        if self.status_bar:
            self.status_bar.update_theme_icon()

    # -------- Language --------

    def _change_language(self, lang: str) -> None:
        if lang not in LANGUAGES or lang == self.lang:
            return
        self.lang = lang
        self.settings.language = lang
        self.settings.save()
        self._rebuild_ui()

    # -------- Hotkeys --------

    def _refresh_hotkeys(self) -> None:
        s = self.settings
        specs = [
            {"combo": s.hotkey_auto_toggle, "mode": "toggle", "on_press": self._hk_toggle_auto},
            {
                "combo": s.hotkey_auto_momentary,
                "mode": "momentary",
                "on_press": self._hk_momentary_press,
                "on_release": self._hk_momentary_release,
            },
            {"combo": s.hotkey_panic, "mode": "toggle", "on_press": self._hk_panic},
        ]
        invalid = self.hotkey_manager.configure(specs)
        # Update hotkeys tab error label
        hk_tab = self.tabs.get("HotkeysTab")
        if isinstance(hk_tab, HotkeysTab):
            hk_tab.set_error(self._t("invalid_combos", x=", ".join(invalid)) if invalid else "")
        # Update status bar
        active = [c for c in (s.hotkey_auto_toggle, s.hotkey_auto_momentary, s.hotkey_panic) if c]
        if self.status_bar:
            self.status_bar.set_hotkeys(active)

    def _hk_toggle_auto(self):
        self.root.after(0, self._toggle_auto_from_hotkey)

    def _toggle_auto_from_hotkey(self):
        auto_tab = self.tabs.get("AutoTab")
        new_state = not auto_tab.auto_var.get() if auto_tab else True
        if auto_tab:
            auto_tab.auto_var.set(new_state)
        self.clicker.set_auto(new_state)
        self._maybe_notify(
            self._t("app_title"),
            self._t("notif_auto_started") if new_state else self._t("notif_auto_stopped"),
        )

    def _hk_momentary_press(self):
        self.root.after(0, lambda: self._set_auto_via_ui(True))

    def _hk_momentary_release(self):
        self.root.after(0, lambda: self._set_auto_via_ui(False))

    def _set_auto_via_ui(self, on: bool):
        auto_tab = self.tabs.get("AutoTab")
        if auto_tab:
            auto_tab.auto_var.set(on)
        self.clicker.set_auto(on)

    def _hk_panic(self):
        self.root.after(0, self._panic_from_hotkey)

    def _panic_from_hotkey(self):
        self.clicker.panic_stop()
        auto_tab = self.tabs.get("AutoTab")
        if auto_tab:
            auto_tab.auto_var.set(False)
        self._maybe_notify(self._t("app_title"), self._t("notif_panic"))

    # -------- Engine -> UI callbacks --------

    def _on_button_seen(self, x, y, button, pressed):
        self.root.after(0, lambda: self._dispatch_button_seen(x, y, button, pressed))

    def _dispatch_button_seen(self, x, y, button, pressed):
        test_tab = self.tabs.get("TestTab")
        if isinstance(test_tab, TestTab):
            test_tab.update_event(x, y, button, pressed)

    def _on_auto_stopped(self, reason: str):
        def update():
            auto_tab = self.tabs.get("AutoTab")
            if auto_tab:
                auto_tab.auto_var.set(False)
            if reason == "limit":
                self._maybe_notify(
                    self._t("app_title"), self._t("notif_limit", n=self.settings.auto_click_limit)
                )

        self.root.after(0, update)

    # -------- Tick --------

    def _tick(self):
        if not self.status_bar:
            self.root.after(100, self._tick)
            return
        if self.clicker.auto_running.is_set():
            extra = ""
            limit = self.clicker.auto_click_limit
            if limit > 0:
                extra = f" ({self.clicker.auto_session_count}/{limit})"
            self.status_bar.set_status(self._t("status_auto") + extra)
        elif self.clicker.holding.is_set():
            self.status_bar.set_status(self._t("status_clicking"))
        elif not self.clicker.hold_enabled.is_set():
            self.status_bar.set_status(self._t("status_hold_disabled"))
        else:
            self.status_bar.set_status(self._t("status_waiting"))
        self.status_bar.set_count(self.clicker.click_count)

        # Cursor in test tab
        try:
            x, y = self.clicker.controller.position
        except (OSError, ValueError):
            pass
        else:
            test_tab = self.tabs.get("TestTab")
            if isinstance(test_tab, TestTab):
                test_tab.update_cursor(int(x), int(y))

        self.root.after(TICK_INTERVAL_MS, self._tick)

    # -------- Shutdown --------

    def _on_close(self):
        logger.info("shutdown requested, closing app")
        self.hotkey_manager.stop()
        self.clicker.shutdown()
        cleanup_socket()
        self.root.destroy()
