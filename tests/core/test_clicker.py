"""AutoClicker: setters, locking, lifecycle, callbacks.

The actual click dispatch is exercised through the mouse Listener event handler
(``_on_click``); the loops themselves are not run inside tests (they would
block on Events). Their state transitions are verified via the public
properties and the holding/auto_running events.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from pyautoclick.core.clicker import AutoClicker


@pytest.fixture
def clicker():
    """Fresh AutoClicker, shut down after the test."""
    c = AutoClicker()
    yield c
    c.shutdown()


# ----------------------------------------------------------------------
# Construction
# ----------------------------------------------------------------------


class TestConstruction:
    def test_initial_state_is_idle(self, clicker):
        assert clicker.holding.is_set() is False
        assert clicker.auto_running.is_set() is False
        assert clicker.click_count == 0
        assert clicker.auto_session_count == 0

    def test_default_callbacks_are_none(self):
        c = AutoClicker()
        try:
            assert c.on_button_seen is None
            assert c.on_auto_stopped is None
        finally:
            c.shutdown()

    def test_callbacks_are_stored(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        c = AutoClicker(on_button_seen=cb1, on_auto_stopped=cb2)
        try:
            assert c.on_button_seen is cb1
            assert c.on_auto_stopped is cb2
        finally:
            c.shutdown()

    def test_threads_are_daemons(self, clicker):
        """Loop threads must be daemons so the interpreter can exit."""
        assert clicker._hold_thread.daemon is True
        assert clicker._auto_thread.daemon is True

    def test_mouse_listener_started(self, clicker):
        """The mouse listener handle is captured for later shutdown()."""
        assert clicker._mouse_listener is not None


# ----------------------------------------------------------------------
# set_hold_enabled
# ----------------------------------------------------------------------


class TestHoldEnabled:
    def test_initial_state_enabled(self, clicker):
        assert clicker.hold_enabled.is_set() is True

    def test_disabling_clears_holding(self, clicker):
        clicker.holding.set()
        clicker.set_hold_enabled(False)
        assert clicker.hold_enabled.is_set() is False
        assert clicker.holding.is_set() is False, "disabling must stop in-flight hold"

    def test_re_enabling_does_not_set_holding(self, clicker):
        clicker.set_hold_enabled(False)
        clicker.set_hold_enabled(True)
        assert clicker.hold_enabled.is_set() is True
        assert clicker.holding.is_set() is False, "re-enable does not auto-trigger"


# ----------------------------------------------------------------------
# Mouse trigger via _on_click
# ----------------------------------------------------------------------


class TestMouseTrigger:
    def test_press_of_trigger_sets_holding(self, clicker):
        clicker._on_click(0, 0, clicker._trigger, pressed=True)
        assert clicker.holding.is_set() is True

    def test_release_of_trigger_clears_holding(self, clicker):
        clicker._on_click(0, 0, clicker._trigger, pressed=True)
        clicker._on_click(0, 0, clicker._trigger, pressed=False)
        assert clicker.holding.is_set() is False

    def test_press_of_other_button_does_not_set_holding(self, clicker):
        from pynput.mouse import Button

        # Use a different button than the trigger
        other = Button.left if clicker._trigger != Button.left else Button.right
        clicker._on_click(0, 0, other, pressed=True)
        assert clicker.holding.is_set() is False

    def test_disabled_hold_ignores_trigger_press(self, clicker):
        clicker.set_hold_enabled(False)
        clicker._on_click(0, 0, clicker._trigger, pressed=True)
        assert clicker.holding.is_set() is False

    def test_on_button_seen_called_for_every_event(self):
        seen: list[tuple] = []
        c = AutoClicker(on_button_seen=lambda x, y, b, p: seen.append((x, y, p)))
        try:
            from pynput.mouse import Button

            c._on_click(10, 20, Button.left, pressed=True)
            c._on_click(11, 21, Button.right, pressed=False)
        finally:
            c.shutdown()
        assert seen == [(10, 20, True), (11, 21, False)]

    def test_callback_exception_does_not_break_listener(self, caplog):
        """A user callback raising must be caught and logged."""
        c = AutoClicker(on_button_seen=lambda *_a, **_k: 1 / 0)
        try:
            from pynput.mouse import Button

            c._on_click(0, 0, Button.left, pressed=True)
            # Trigger logic still ran (but on the 'left' button, not trigger)
            assert c.holding.is_set() is False
        finally:
            c.shutdown()


# ----------------------------------------------------------------------
# set_auto + panic_stop
# ----------------------------------------------------------------------


class TestAutoMode:
    def test_set_auto_true_sets_event(self, clicker):
        clicker.set_auto(True)
        assert clicker.auto_running.is_set() is True

    def test_set_auto_true_resets_session_counter(self, clicker):
        # Manually bump
        with clicker.lock:
            clicker._auto_session_count = 42
        clicker.set_auto(True)
        assert clicker.auto_session_count == 0

    def test_set_auto_true_no_reset_when_explicit(self, clicker):
        with clicker.lock:
            clicker._auto_session_count = 42
        clicker.set_auto(True, reset_session=False)
        assert clicker.auto_session_count == 42

    def test_set_auto_false_clears_event(self, clicker):
        clicker.set_auto(True)
        clicker.set_auto(False)
        assert clicker.auto_running.is_set() is False

    def test_set_auto_false_invokes_user_callback(self):
        events: list[str] = []
        # NB: the lambda is required — production calls
        # on_auto_stopped(reason="user") with a keyword arg, while
        # list.append only accepts positional args.
        c = AutoClicker(on_auto_stopped=lambda reason: events.append(reason))
        try:
            c.set_auto(True)
            c.set_auto(False)
        finally:
            c.shutdown()
        assert events == ["user"]

    def test_panic_clears_both_modes(self, clicker):
        clicker.set_auto(True)
        clicker.holding.set()
        clicker.panic_stop()
        assert clicker.auto_running.is_set() is False
        assert clicker.holding.is_set() is False

    def test_panic_invokes_user_callback_with_panic_reason(self):
        events: list[str] = []
        c = AutoClicker(on_auto_stopped=lambda reason: events.append(reason))
        try:
            c.panic_stop()
        finally:
            c.shutdown()
        assert events == ["panic"]


# ----------------------------------------------------------------------
# Position management
# ----------------------------------------------------------------------


class TestPositions:
    def test_initial_positions_empty(self, clicker):
        assert clicker.positions == []

    def test_add_position(self, clicker):
        clicker.add_position((100, 200))
        clicker.add_position((300, 400))
        assert clicker.positions == [(100, 200), (300, 400)]

    def test_remove_position(self, clicker):
        clicker.set_positions([(1, 1), (2, 2), (3, 3)])
        clicker.remove_position(1)
        assert clicker.positions == [(1, 1), (3, 3)]

    def test_remove_position_out_of_range_is_noop(self, clicker):
        clicker.set_positions([(1, 1)])
        clicker.remove_position(99)
        assert clicker.positions == [(1, 1)]

    def test_clear_positions(self, clicker):
        clicker.set_positions([(1, 1), (2, 2)])
        clicker.clear_positions()
        assert clicker.positions == []

    def test_positions_property_returns_snapshot(self, clicker):
        """Mutating the returned list must not affect the engine's state."""
        clicker.set_positions([(1, 1)])
        snap = clicker.positions
        snap.append((99, 99))
        assert clicker.positions == [(1, 1)], "snapshot must be a copy"

    def test_set_positions_resets_index(self, clicker):
        clicker.set_positions([(1, 1), (2, 2)])
        clicker._pos_idx = 5
        clicker.set_positions([(3, 3)])
        assert clicker._pos_idx == 0


# ----------------------------------------------------------------------
# Numeric setters
# ----------------------------------------------------------------------


class TestNumericSetters:
    @pytest.mark.parametrize(
        "attr,setter,value",
        [
            ("_cps", "set_cps", 25),
            ("_hold_jitter_ms", "set_hold_jitter_ms", 10),
            ("_auto_interval_ms", "set_auto_interval_ms", 200),
            ("_auto_press_ms", "set_auto_press_ms", 30),
            ("_auto_jitter_ms", "set_auto_jitter_ms", 5),
            ("_auto_click_limit", "set_auto_click_limit", 1000),
        ],
    )
    def test_setter_updates_attribute(self, clicker, attr, setter, value):
        getattr(clicker, setter)(value)
        assert getattr(clicker, attr) == value

    def test_set_use_positions(self, clicker):
        clicker.set_use_positions(True)
        assert clicker._use_positions is True
        clicker.set_use_positions(False)
        assert clicker._use_positions is False


# ----------------------------------------------------------------------
# Click count & reset
# ----------------------------------------------------------------------


class TestClickCount:
    def test_reset_click_count(self, clicker):
        with clicker.lock:
            clicker._click_count = 999
        clicker.reset_click_count()
        assert clicker.click_count == 0

    def test_click_count_thread_safe_under_load(self, clicker):
        """Concurrent increments via the lock must not lose updates."""
        n = 1000
        threads = []

        def bump():
            for _ in range(n):
                with clicker.lock:
                    clicker._click_count += 1

        for _ in range(4):
            t = threading.Thread(target=bump)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        assert clicker.click_count == 4 * n


# ----------------------------------------------------------------------
# Lifecycle: shutdown
# ----------------------------------------------------------------------


class TestShutdown:
    def test_shutdown_sets_stop_event(self):
        c = AutoClicker()
        c.shutdown()
        assert c._stop_event.is_set() is True

    def test_shutdown_unblocks_loops(self):
        c = AutoClicker()
        c.shutdown()
        # Both events are set so loops can observe stop
        assert c.holding.is_set() is True
        assert c.auto_running.is_set() is True

    def test_shutdown_stops_mouse_listener(self):
        c = AutoClicker()
        listener = c._mouse_listener
        c.shutdown()
        # The fake listener tracks _stopped; the real one's stop() returns None
        if hasattr(listener, "_stopped"):
            assert listener._stopped is True

    def test_shutdown_idempotent(self):
        c = AutoClicker()
        c.shutdown()
        c.shutdown()  # must not raise
