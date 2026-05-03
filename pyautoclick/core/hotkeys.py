"""Global hotkey manager: single keyboard listener, multiple bindings."""

from __future__ import annotations

import logging
import threading

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Listener unique qui dispatche vers plusieurs bindings.

    Each binding is a dict ``{combo, mode, on_press, on_release?}`` where
    ``mode`` is ``"toggle"`` (callback once when all keys pressed) or
    ``"momentary"`` (callbacks at full-press and full-release).
    """

    def __init__(self):
        self.listener: keyboard.Listener | None = None
        self.bindings: list[dict] = []
        self.pressed: set = set()
        self._lock = threading.Lock()

    def configure(self, specs: list[dict]) -> list[str]:
        """(Re)configure the listener with the given bindings.

        Returns the list of combo strings that failed to parse.
        """
        self.stop()
        new_bindings = []
        invalid: list[str] = []
        for spec in specs:
            combo = (spec.get("combo") or "").strip()
            if not combo:
                continue
            try:
                keys = frozenset(keyboard.HotKey.parse(combo))
            except (ValueError, TypeError):
                logger.warning("invalid hotkey combo %r — ignored", combo)
                invalid.append(combo)
                continue
            new_bindings.append(
                {
                    "combo": combo,
                    "keys": keys,
                    "mode": spec["mode"],
                    "on_press": spec.get("on_press"),
                    "on_release": spec.get("on_release"),
                    "active": False,
                }
            )
        with self._lock:
            self.bindings = new_bindings
            self.pressed = set()
        if new_bindings:
            self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.listener.start()
        return invalid

    def stop(self) -> None:
        if self.listener is not None:
            try:
                self.listener.stop()
            except (RuntimeError, OSError):
                logger.exception("error stopping keyboard listener")
            self.listener = None

    def _canonical(self, key):
        if self.listener is not None:
            try:
                return self.listener.canonical(key)
            except (AttributeError, ValueError):
                return key
        return key

    def _on_press(self, key):
        ck = self._canonical(key)
        with self._lock:
            self.pressed.add(ck)
            for b in self.bindings:
                if not b["active"] and b["keys"].issubset(self.pressed):
                    b["active"] = True
                    cb = b["on_press"]
                    if cb:
                        try:
                            cb()
                        except Exception:  # never let user callback kill the listener
                            logger.exception("hotkey on_press callback raised")

    def _on_release(self, key):
        ck = self._canonical(key)
        with self._lock:
            self.pressed.discard(ck)
            for b in self.bindings:
                if b["active"] and not b["keys"].issubset(self.pressed):
                    b["active"] = False
                    if b["mode"] == "momentary":
                        cb = b["on_release"]
                        if cb:
                            try:
                                cb()
                            except Exception:  # never let user callback kill the listener
                                logger.exception("hotkey on_release callback raised")
