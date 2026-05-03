"""Cross-platform desktop notifications.

Backends, in order of preference:
- Linux: ``notify-send`` (libnotify)
- macOS: ``osascript`` (display notification)
- Windows: PowerShell BurntToast (best-effort) or fallback to console log

If no backend is available the call is silently a no-op — notifications
are never load-bearing.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)


def _notify_linux(title: str, message: str) -> bool:
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.Popen(
            ["notify-send", "-a", "PyAutoClick", title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        logger.debug("notify-send launch failed", exc_info=True)
        return False


def _notify_macos(title: str, message: str) -> bool:
    if not shutil.which("osascript"):
        return False
    # Escape double quotes in user-facing strings (i18n keeps these safe in
    # practice but defensive escaping costs nothing).
    safe_t = title.replace('"', '\\"')
    safe_m = message.replace('"', '\\"')
    script = f'display notification "{safe_m}" with title "{safe_t}"'
    try:
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        logger.debug("osascript launch failed", exc_info=True)
        return False


def _notify_windows(title: str, message: str) -> bool:
    # Best-effort via PowerShell BurntToast if installed; otherwise log only.
    if not shutil.which("powershell"):
        return False
    safe_t = title.replace("'", "''")
    safe_m = message.replace("'", "''")
    ps = (
        "if (Get-Module -ListAvailable -Name BurntToast) {"
        f"  New-BurntToastNotification -Text '{safe_t}','{safe_m}'"
        "}"
    )
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except OSError:
        logger.debug("powershell launch failed", exc_info=True)
        return False


def notify(title: str, message: str) -> None:
    """Send a desktop notification. Silent on unsupported platforms."""
    if sys.platform.startswith("linux"):
        ok = _notify_linux(title, message)
    elif sys.platform == "darwin":
        ok = _notify_macos(title, message)
    elif sys.platform == "win32":
        ok = _notify_windows(title, message)
    else:
        ok = False

    if not ok:
        # Never fail loudly — we just record it for the log.
        logger.debug("notification not delivered: %s — %s", title, message)
