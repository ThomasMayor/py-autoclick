"""Context objects passed to UI components (tabs, status bar).

Three small role-specific contexts replace what used to be a single 8-field
``AppContext``:

- :class:`StateContext`  — what to read/mutate (settings + clicker)
- :class:`ServicesContext` — fire-and-forget side effects (i18n, notify, status)
- :class:`LifecycleContext` — orchestrator-owned actions (theme, language, hotkeys)

The aggregator :class:`AppContext` just bundles them and exposes shortcut
properties so existing tab code (``ctx.t``, ``ctx.settings``…) keeps working.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pyautoclick.core.clicker import AutoClicker
from pyautoclick.core.platform_capabilities import PlatformCapabilities
from pyautoclick.persistence.settings import Settings


@dataclass(frozen=True)
class StateContext:
    """Read/write app state. Tabs mutate ``settings`` then call ``commit()``."""

    settings: Settings
    clicker: AutoClicker
    commit: Callable[[], None]              # persist settings to disk


@dataclass(frozen=True)
class ServicesContext:
    """Stateless effects: i18n, notifications, transient status bar messages."""

    t: Callable[..., str]                   # t(key, **kwargs) -> str
    notify: Callable[[str, str], None]      # respects notify_enabled toggle
    set_status: Callable[[str], None]       # transient status bar message


@dataclass(frozen=True)
class LifecycleContext:
    """Orchestrator-owned actions + platform info."""

    get_theme: Callable[[], str]
    toggle_theme: Callable[[], None]
    change_language: Callable[[str], None]
    refresh_hotkeys: Callable[[], None]
    capabilities: PlatformCapabilities


@dataclass(frozen=True)
class AppContext:
    """Aggregator. Use the typed sub-contexts when possible."""

    state: StateContext
    services: ServicesContext
    lifecycle: LifecycleContext

    # ---- Backwards-compatible shortcuts (used by existing tabs) ----
    @property
    def settings(self) -> Settings:
        return self.state.settings

    @property
    def clicker(self) -> AutoClicker:
        return self.state.clicker

    @property
    def commit(self) -> Callable[[], None]:
        return self.state.commit

    @property
    def t(self) -> Callable[..., str]:
        return self.services.t

    @property
    def notify(self) -> Callable[[str, str], None]:
        return self.services.notify

    @property
    def set_status(self) -> Callable[[str], None]:
        return self.services.set_status

    @property
    def get_theme(self) -> Callable[[], str]:
        return self.lifecycle.get_theme

    @property
    def toggle_theme(self) -> Callable[[], None]:
        return self.lifecycle.toggle_theme

    @property
    def change_language(self) -> Callable[[str], None]:
        return self.lifecycle.change_language

    @property
    def refresh_hotkeys(self) -> Callable[[], None]:
        return self.lifecycle.refresh_hotkeys

    @property
    def capabilities(self) -> PlatformCapabilities:
        return self.lifecycle.capabilities
