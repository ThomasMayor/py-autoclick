"""Shared pytest fixtures + fake pynput injection for headless test runs.

Why the fake pynput?
--------------------
Pynput's xorg backend tries to acquire an X display at import time. On
machines without a display server (headless CI, containers, CLI tools
running over SSH), ``import pynput`` raises ``ImportError`` immediately.

Production code already keeps pynput out of import-time paths through the
``_ButtonMap`` lazy proxy in ``core/buttons.py`` and the ``core/timing.py``
extraction. But tests for ``core/clicker`` and ``core/hotkeys`` need to
exercise code that does ``from pynput import mouse`` / ``from pynput import
keyboard`` at module load.

To allow those tests to run anywhere, we inject a minimal fake into
``sys.modules`` **only if the real pynput cannot be imported**. When the
real pynput is available (DISPLAY set, valid xorg backend), it wins and
tests run against the real classes — no fakery.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fake pynput injection (only if the real one cannot import)
# ---------------------------------------------------------------------------


def _install_fake_pynput() -> None:
    """Populate sys.modules with a minimal fake pynput package."""

    class _Btn:
        """Stand-in for ``pynput.mouse.Button``: comparable, hashable."""

        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return f"Button.{self.name}"

        def __eq__(self, other: object) -> bool:
            return isinstance(other, _Btn) and self.name == other.name

        def __hash__(self) -> int:
            return hash(("FakeButton", self.name))

    class _ButtonNamespace:
        button8 = _Btn("button8")
        button9 = _Btn("button9")
        middle = _Btn("middle")
        right = _Btn("right")
        left = _Btn("left")

    class _Controller:
        """Mock ``pynput.mouse.Controller``."""

        def __init__(self) -> None:
            self.position: tuple[int, int] = (0, 0)
            self.click = MagicMock()
            self.press = MagicMock()
            self.release = MagicMock()

    class _MouseListener:
        """Mock ``pynput.mouse.Listener`` — does NOT spawn a real thread."""

        def __init__(self, on_click=None, **_kw) -> None:
            self.on_click = on_click
            self.daemon = False
            self._started = False
            self._stopped = False

        def start(self) -> None:
            self._started = True

        def stop(self) -> None:
            self._stopped = True

        def canonical(self, key):
            return key

    class _HotKey:
        """Mock ``pynput.keyboard.HotKey`` — only ``parse`` is needed in tests."""

        @staticmethod
        def parse(combo: str):
            # Real pynput returns a frozenset of Key/KeyCode. Tests only need
            # consistent hashable elements, so we split by '+' and yield
            # placeholder strings. ValueErrors must propagate for unparseable
            # combos so the HotkeyManager invalid-list logic stays exercised.
            if not combo or "++" in combo or combo.startswith("+") or combo.endswith("+"):
                raise ValueError(f"unparseable: {combo!r}")
            return [p.strip() for p in combo.split("+") if p.strip()]

    class _KeyboardListener:
        def __init__(self, on_press=None, on_release=None, **_kw) -> None:
            self.on_press = on_press
            self.on_release = on_release
            self._started = False
            self._stopped = False

        def start(self) -> None:
            self._started = True

        def stop(self) -> None:
            self._stopped = True

        def canonical(self, key):
            return key

    fake_mouse = ModuleType("pynput.mouse")
    fake_mouse.Button = _ButtonNamespace
    fake_mouse.Controller = _Controller
    fake_mouse.Listener = _MouseListener

    fake_keyboard = ModuleType("pynput.keyboard")
    fake_keyboard.HotKey = _HotKey
    fake_keyboard.Listener = _KeyboardListener

    fake_pynput = ModuleType("pynput")
    fake_pynput.mouse = fake_mouse
    fake_pynput.keyboard = fake_keyboard

    sys.modules["pynput"] = fake_pynput
    sys.modules["pynput.mouse"] = fake_mouse
    sys.modules["pynput.keyboard"] = fake_keyboard


# Try the real pynput first. If it fails (no DISPLAY, missing native lib),
# fall back to the fake so tests can still import core/clicker, core/hotkeys.
if "pynput" not in sys.modules:
    try:
        import pynput  # noqa: F401
    except ImportError:
        _install_fake_pynput()


# ---------------------------------------------------------------------------
# tmp_config_dir / write_config fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Iterator[Path]:
    """Patch CONFIG_DIR / CONFIG_FILE to a fresh temp dir for each test."""
    cfg_dir = tmp_path / "autoclicker"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.json"
    lock_file = cfg_dir / "app.lock"
    sock_file = cfg_dir / "app.sock"
    targets = [
        "pyautoclick.persistence.settings.CONFIG_DIR",
        "pyautoclick.persistence.settings.CONFIG_FILE",
        "pyautoclick.core.single_instance.CONFIG_DIR",
        "pyautoclick.core.single_instance.LOCK_FILE",
        "pyautoclick.core.single_instance.SOCKET_FILE",
    ]
    patches = []
    values = {
        "CONFIG_DIR": cfg_dir,
        "CONFIG_FILE": cfg_file,
        "LOCK_FILE": lock_file,
        "SOCKET_FILE": sock_file,
    }
    for tgt in targets:
        name = tgt.rsplit(".", 1)[1]
        patches.append(patch(tgt, values[name]))
    for p in patches:
        p.start()
    try:
        yield cfg_dir
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def write_config(tmp_config_dir: Path):
    """Helper to drop a JSON config into the temp dir."""
    cfg_file = tmp_config_dir / "config.json"

    def _write(data: dict) -> Path:
        cfg_file.write_text(json.dumps(data))
        return cfg_file

    return _write
