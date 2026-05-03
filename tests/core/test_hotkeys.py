"""HotkeyManager: configure, callback dispatch, listener lifecycle.

These tests use the fake pynput injected by tests/conftest.py when the real
one is not importable. The fake's ``HotKey.parse`` is a simple ``+``-split
that raises ``ValueError`` for malformed combos — enough to exercise the
HotkeyManager's invalid-list path and dispatch logic.
"""

from __future__ import annotations

import pytest

from pyautoclick.core.hotkeys import HotkeyManager


@pytest.fixture
def hm():
    """Fresh HotkeyManager, stopped after the test."""
    h = HotkeyManager()
    yield h
    h.stop()


# ----------------------------------------------------------------------
# configure(): parsing + invalid combo collection
# ----------------------------------------------------------------------


class TestConfigure:
    def test_empty_specs_does_not_start_listener(self, hm):
        invalid = hm.configure([])
        assert invalid == []
        assert hm.listener is None, "no listener should be started for zero bindings"

    def test_specs_with_blank_combo_are_ignored(self, hm):
        invalid = hm.configure(
            [
                {"combo": "", "mode": "toggle"},
                {"combo": "   ", "mode": "toggle"},
            ]
        )
        assert invalid == []
        assert hm.listener is None

    def test_invalid_combo_returned_in_invalid_list(self, hm):
        """Combos that fail to parse are listed; valid ones still register."""
        # "++" is unparseable in our fake (and real) HotKey.parse
        invalid = hm.configure(
            [
                {"combo": "++", "mode": "toggle"},
                {"combo": "ctrl+a", "mode": "toggle"},
            ]
        )
        assert "++" in invalid
        # The valid one is registered
        assert len(hm.bindings) == 1
        assert hm.bindings[0]["combo"] == "ctrl+a"

    def test_valid_combos_register_with_correct_mode(self, hm):
        hm.configure(
            [
                {"combo": "ctrl+a", "mode": "toggle", "on_press": lambda: None},
                {
                    "combo": "ctrl+b",
                    "mode": "momentary",
                    "on_press": lambda: None,
                    "on_release": lambda: None,
                },
            ]
        )
        modes = [b["mode"] for b in hm.bindings]
        assert modes == ["toggle", "momentary"]

    def test_configure_starts_listener_when_specs_present(self, hm):
        hm.configure([{"combo": "ctrl+a", "mode": "toggle"}])
        assert hm.listener is not None

    def test_reconfigure_replaces_previous_bindings(self, hm):
        hm.configure([{"combo": "ctrl+a", "mode": "toggle"}])
        hm.configure([{"combo": "ctrl+b", "mode": "toggle"}])
        combos = [b["combo"] for b in hm.bindings]
        assert combos == ["ctrl+b"], "previous binding must be discarded"

    def test_reconfigure_resets_pressed_set(self, hm):
        hm.configure([{"combo": "ctrl+a", "mode": "toggle"}])
        hm.pressed.add("phantom")
        hm.configure([{"combo": "ctrl+b", "mode": "toggle"}])
        assert hm.pressed == set(), "pressed set must be reset on reconfigure"


# ----------------------------------------------------------------------
# stop()
# ----------------------------------------------------------------------


class TestStop:
    def test_stop_clears_listener(self, hm):
        hm.configure([{"combo": "ctrl+a", "mode": "toggle"}])
        assert hm.listener is not None
        hm.stop()
        assert hm.listener is None, "listener reference cleared after stop"

    def test_stop_when_no_listener_does_not_raise(self, hm):
        # Fresh manager, never configured
        hm.stop()  # must not raise

    def test_stop_idempotent(self, hm):
        hm.configure([{"combo": "ctrl+a", "mode": "toggle"}])
        hm.stop()
        hm.stop()  # second call must not raise


# ----------------------------------------------------------------------
# Callback dispatch (toggle vs momentary)
# ----------------------------------------------------------------------


class TestDispatch:
    def test_toggle_fires_on_full_press(self, hm):
        calls: list[str] = []
        hm.configure(
            [
                {"combo": "a+b", "mode": "toggle", "on_press": lambda: calls.append("fired")},
            ]
        )
        # Simulate keys pressed in order
        hm._on_press("a")
        assert calls == [], "single key not enough for combo"
        hm._on_press("b")
        assert calls == ["fired"], "full combo must fire callback"

    def test_toggle_does_not_fire_twice_on_repeated_press(self, hm):
        """Once active, toggle must not refire while keys are still held."""
        calls: list[str] = []
        hm.configure(
            [
                {"combo": "a", "mode": "toggle", "on_press": lambda: calls.append("fired")},
            ]
        )
        hm._on_press("a")
        hm._on_press("a")  # repeat (keyboard auto-repeat)
        assert calls == ["fired"], "toggle must fire exactly once per combo cycle"

    def test_toggle_can_refire_after_release(self, hm):
        calls: list[str] = []
        hm.configure(
            [
                {"combo": "a", "mode": "toggle", "on_press": lambda: calls.append("fired")},
            ]
        )
        hm._on_press("a")
        hm._on_release("a")
        hm._on_press("a")
        assert len(calls) == 2, "toggle must fire again after a full release cycle"

    def test_momentary_fires_press_and_release(self, hm):
        events: list[str] = []
        hm.configure(
            [
                {
                    "combo": "a",
                    "mode": "momentary",
                    "on_press": lambda: events.append("press"),
                    "on_release": lambda: events.append("release"),
                },
            ]
        )
        hm._on_press("a")
        hm._on_release("a")
        assert events == ["press", "release"]

    def test_toggle_does_not_fire_on_release(self, hm):
        """Toggle mode never invokes on_release callback."""
        events: list[str] = []
        hm.configure(
            [
                {
                    "combo": "a",
                    "mode": "toggle",
                    "on_press": lambda: events.append("press"),
                    "on_release": lambda: events.append("release"),
                },
            ]
        )
        hm._on_press("a")
        hm._on_release("a")
        assert events == ["press"], "toggle must not invoke on_release"

    def test_callback_exception_does_not_kill_dispatch(self, hm, caplog):
        """A user callback raising must be caught; subsequent bindings still fire."""
        good_calls: list[str] = []

        def bad():
            raise RuntimeError("user bug")

        hm.configure(
            [
                {"combo": "a", "mode": "toggle", "on_press": bad},
                {"combo": "a", "mode": "toggle", "on_press": lambda: good_calls.append("ok")},
            ]
        )
        hm._on_press("a")
        assert good_calls == ["ok"], "second binding must still fire after first one raised"


# ----------------------------------------------------------------------
# Multi-binding interactions
# ----------------------------------------------------------------------


class TestMultipleBindings:
    def test_independent_bindings_fire_independently(self, hm):
        a_calls: list[str] = []
        b_calls: list[str] = []
        hm.configure(
            [
                {"combo": "a", "mode": "toggle", "on_press": lambda: a_calls.append("a")},
                {"combo": "b", "mode": "toggle", "on_press": lambda: b_calls.append("b")},
            ]
        )
        hm._on_press("a")
        assert a_calls == ["a"]
        assert b_calls == []
        hm._on_press("b")
        assert a_calls == ["a"]
        assert b_calls == ["b"]
