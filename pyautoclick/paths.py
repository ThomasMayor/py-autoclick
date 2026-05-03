"""Filesystem paths used across the app.

Cross-platform notes
--------------------
- Config lives in the platform-appropriate user config dir
  (``~/.config/autoclicker`` on Linux/macOS; ``%APPDATA%\\autoclicker`` on Windows).
- The icon is shipped inside the wheel as a package resource and resolved via
  :func:`importlib.resources` so it works regardless of install location.
"""

from __future__ import annotations

import os
import sys
from importlib import resources
from pathlib import Path


def _user_config_dir() -> Path:
    """Return the platform-appropriate user config directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "autoclicker"
    # XDG_CONFIG_HOME on Linux, fallback to ~/.config (also macOS convention here)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "autoclicker"
    return Path.home() / ".config" / "autoclicker"


CONFIG_DIR = _user_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"
LOCK_FILE = CONFIG_DIR / "app.lock"
SOCKET_FILE = CONFIG_DIR / "app.sock"


def icon_path() -> Path:
    """Resolve the bundled icon. Works in dev (editable) and wheel installs."""
    try:
        # importlib.resources returns a context manager for binary access; for
        # tk.PhotoImage we need a real filesystem path.
        ref = resources.files("pyautoclick").joinpath("assets/py-autoclick.png")
        path = Path(str(ref))
        if path.exists():
            return path
    except (ModuleNotFoundError, FileNotFoundError, AttributeError):
        pass
    # Fallback: dev layout (project root next to the package directory)
    return Path(__file__).resolve().parent.parent / "py-autoclick.png"


# Backwards-compat constant; prefer ``icon_path()`` going forward.
ICON_PATH = icon_path()
