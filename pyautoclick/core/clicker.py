"""Click engine: hold mode + auto mode running on background threads.

Thread safety
-------------
All mutable state shared between the listener / loop threads and the UI
thread is protected by ``self.lock``. Setters used from the UI must go
through the explicit setter methods (``set_*``); the loops snapshot values
under the lock at the start of each iteration to avoid torn reads.

Lifecycle
---------
The mouse ``Listener`` handle is captured so it can be ``stop()``-ed at
shutdown via :meth:`shutdown`. The two loop threads are daemons; they exit
when the interpreter does, but :meth:`shutdown` also clears their wait
events to give them a chance to exit cleanly first.
"""

from __future__ import annotations

import logging
import random
import threading
import time

from pynput import mouse
from pynput.mouse import Button, Controller

logger = logging.getLogger(__name__)


def jittered(value_ms: float, jitter_ms: float) -> float:
    if jitter_ms <= 0:
        return max(0, value_ms)
    return max(0, value_ms + random.uniform(-jitter_ms, jitter_ms))


class AutoClicker:
    """Two background loops: hold (gated by mouse trigger) and auto (free-running)."""

    def __init__(self, on_button_seen=None, on_auto_stopped=None):
        self.controller = Controller()
        self.lock = threading.RLock()  # all mutable state below

        # Mode maintenu
        self.hold_enabled = threading.Event()
        self.hold_enabled.set()
        self.holding = threading.Event()
        self._cps = 15
        self._hold_jitter_ms = 0
        self._trigger = Button.button8
        self._click_btn = Button.left

        # Mode automatique
        self.auto_running = threading.Event()
        self._auto_btn = Button.left
        self._auto_interval_ms = 100
        self._auto_press_ms = 10
        self._auto_jitter_ms = 0
        self._auto_click_limit = 0
        self._auto_session_count = 0
        self._use_positions = False
        self._positions: list[tuple[int, int]] = []
        self._pos_idx = 0

        self._click_count = 0

        self.on_button_seen = on_button_seen
        self.on_auto_stopped = on_auto_stopped

        # Lifecycle
        self._stop_event = threading.Event()
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()
        self._hold_thread = threading.Thread(
            target=self._hold_loop,
            name="autoclicker-hold",
            daemon=True,
        )
        self._auto_thread = threading.Thread(
            target=self._auto_loop,
            name="autoclicker-auto",
            daemon=True,
        )
        self._hold_thread.start()
        self._auto_thread.start()

    # ------------------------------------------------------------------
    # Read-only properties (locked snapshots) for UI tick
    # ------------------------------------------------------------------

    @property
    def click_count(self) -> int:
        with self.lock:
            return self._click_count

    @property
    def auto_session_count(self) -> int:
        with self.lock:
            return self._auto_session_count

    @property
    def auto_click_limit(self) -> int:
        with self.lock:
            return self._auto_click_limit

    @property
    def positions(self) -> list[tuple[int, int]]:
        # Returns a snapshot; mutating it doesn't affect the engine.
        # Use ``set_positions``/``add_position``/``clear_positions`` instead.
        with self.lock:
            return list(self._positions)

    # ------------------------------------------------------------------
    # Loops
    # ------------------------------------------------------------------

    def _hold_loop(self) -> None:
        while not self._stop_event.is_set():
            self.holding.wait()
            if self._stop_event.is_set():
                return
            with self.lock:
                btn = self._click_btn
                cps = self._cps
                jitter = self._hold_jitter_ms
            self.controller.click(btn)
            with self.lock:
                self._click_count += 1
            base = 1000.0 / max(1, cps)
            time.sleep(jittered(base, jitter) / 1000.0)

    def _auto_loop(self) -> None:
        while not self._stop_event.is_set():
            self.auto_running.wait()
            if self._stop_event.is_set():
                return

            with self.lock:
                use_positions = self._use_positions
                positions_snapshot = list(self._positions)
                pos_idx = self._pos_idx
                btn = self._auto_btn
                press_ms = self._auto_press_ms
                jitter = self._auto_jitter_ms
                interval_ms = self._auto_interval_ms
                limit = self._auto_click_limit

            if use_positions and positions_snapshot:
                pos = positions_snapshot[pos_idx % len(positions_snapshot)]
                with self.lock:
                    self._pos_idx += 1
                try:
                    self.controller.position = pos
                except (ValueError, OSError):
                    logger.exception("failed to move cursor to %r", pos)

            self.controller.press(btn)
            time.sleep(jittered(press_ms, jitter) / 1000.0)
            self.controller.release(btn)

            with self.lock:
                self._click_count += 1
                self._auto_session_count += 1
                reached = limit > 0 and self._auto_session_count >= limit

            if reached:
                self.auto_running.clear()
                if self.on_auto_stopped:
                    self.on_auto_stopped(reason="limit")
                continue

            time.sleep(jittered(interval_ms, jitter) / 1000.0)

    # ------------------------------------------------------------------
    # Mouse listener
    # ------------------------------------------------------------------

    def _on_click(self, x, y, button, pressed):
        if self.on_button_seen:
            try:
                self.on_button_seen(x, y, button, pressed)
            except Exception:  # never let a UI callback crash the listener
                logger.exception("on_button_seen callback raised")
        if not self.hold_enabled.is_set():
            self.holding.clear()
            return
        with self.lock:
            trigger = self._trigger
        if button == trigger:
            if pressed:
                self.holding.set()
            else:
                self.holding.clear()

    # ------------------------------------------------------------------
    # Setters (UI-thread)
    # ------------------------------------------------------------------

    def set_trigger(self, btn: Button) -> None:
        with self.lock:
            self._trigger = btn
        self.holding.clear()

    def set_click_btn(self, btn: Button) -> None:
        with self.lock:
            self._click_btn = btn

    def set_cps(self, cps: int) -> None:
        with self.lock:
            self._cps = cps

    def set_hold_jitter_ms(self, ms: int) -> None:
        with self.lock:
            self._hold_jitter_ms = ms

    def set_auto_btn(self, btn: Button) -> None:
        with self.lock:
            self._auto_btn = btn

    def set_auto_interval_ms(self, ms: int) -> None:
        with self.lock:
            self._auto_interval_ms = ms

    def set_auto_press_ms(self, ms: int) -> None:
        with self.lock:
            self._auto_press_ms = ms

    def set_auto_jitter_ms(self, ms: int) -> None:
        with self.lock:
            self._auto_jitter_ms = ms

    def set_auto_click_limit(self, n: int) -> None:
        with self.lock:
            self._auto_click_limit = n

    def set_use_positions(self, on: bool) -> None:
        with self.lock:
            self._use_positions = on

    def set_positions(self, positions: list[tuple[int, int]]) -> None:
        with self.lock:
            self._positions = list(positions)
            self._pos_idx = 0

    def add_position(self, pos: tuple[int, int]) -> None:
        with self.lock:
            self._positions.append(pos)

    def remove_position(self, idx: int) -> None:
        with self.lock:
            if 0 <= idx < len(self._positions):
                del self._positions[idx]

    def clear_positions(self) -> None:
        with self.lock:
            self._positions.clear()
            self._pos_idx = 0

    def set_hold_enabled(self, on: bool) -> None:
        if on:
            self.hold_enabled.set()
        else:
            self.hold_enabled.clear()
            self.holding.clear()

    def set_auto(self, on: bool, *, reset_session: bool = True) -> None:
        if on:
            if reset_session:
                with self.lock:
                    self._auto_session_count = 0
                    self._pos_idx = 0
            self.auto_running.set()
        else:
            was = self.auto_running.is_set()
            self.auto_running.clear()
            if was and self.on_auto_stopped:
                self.on_auto_stopped(reason="user")

    def reset_click_count(self) -> None:
        with self.lock:
            self._click_count = 0

    def panic_stop(self) -> None:
        self.auto_running.clear()
        self.holding.clear()
        if self.on_auto_stopped:
            self.on_auto_stopped(reason="panic")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop the mouse listener and unblock both loop threads.

        Safe to call multiple times. After calling, the clicker is unusable.
        """
        if self._stop_event.is_set():
            return
        logger.info("shutting down clicker")
        self._stop_event.set()
        # Wake up both wait()s so the loops can observe _stop_event
        self.holding.set()
        self.auto_running.set()
        try:
            self._mouse_listener.stop()
        except (RuntimeError, OSError):
            logger.exception("error stopping mouse listener")
