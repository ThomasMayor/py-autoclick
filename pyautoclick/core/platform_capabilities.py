"""Runtime detection of OS + display server + expected pynput capabilities.

The detection is conservative: when in doubt, we assume the capability is
*not* available so the UI surfaces a warning rather than silently failing.

Capability matrix (best-effort, based on pynput 1.7 behaviour as of 2026):

| Display server      | mouse listener | keyboard listener (global hotkeys)     |
|---------------------|----------------|----------------------------------------|
| Linux X11           | yes            | yes                                    |
| Linux Wayland       | partial (XWayland windows only) | usually no — Wayland blocks
|                     |                | global keyboard grabbing for security  |
| macOS               | yes (with Accessibility permission)                       |
| Windows             | yes            | yes                                    |
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlatformCapabilities:
    os_name: str  # "linux" | "macos" | "windows" | other
    display_server: str  # "x11" | "wayland" | "macos" | "windows" | "unknown"
    has_global_hotkeys: bool
    has_global_mouse_events: bool
    caveats: list[str] = field(default_factory=list)


def detect() -> PlatformCapabilities:
    """Inspect environment variables and ``sys.platform`` to guess capabilities."""
    if sys.platform == "win32":
        return PlatformCapabilities(
            os_name="windows",
            display_server="windows",
            has_global_hotkeys=True,
            has_global_mouse_events=True,
            caveats=[],
        )

    if sys.platform == "darwin":
        return PlatformCapabilities(
            os_name="macos",
            display_server="macos",
            has_global_hotkeys=True,
            has_global_mouse_events=True,
            caveats=[
                "macos_accessibility_required",
            ],
        )

    if sys.platform.startswith("linux"):
        session = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        if session == "wayland" or (not session and wayland_display):
            return PlatformCapabilities(
                os_name="linux",
                display_server="wayland",
                # Conservative: assume hotkeys/mouse don't work on Wayland.
                # In practice both depend on whether XWayland forwards events,
                # which depends on focused window type (X11 vs native Wayland).
                has_global_hotkeys=False,
                has_global_mouse_events=False,
                caveats=[
                    "wayland_hotkeys_blocked",
                    "wayland_mouse_xwayland_only",
                ],
            )
        if session == "x11" or os.environ.get("DISPLAY"):
            return PlatformCapabilities(
                os_name="linux",
                display_server="x11",
                has_global_hotkeys=True,
                has_global_mouse_events=True,
                caveats=[],
            )
        return PlatformCapabilities(
            os_name="linux",
            display_server="unknown",
            has_global_hotkeys=False,
            has_global_mouse_events=False,
            caveats=["unknown_display_server"],
        )

    return PlatformCapabilities(
        os_name=sys.platform,
        display_server="unknown",
        has_global_hotkeys=False,
        has_global_mouse_events=False,
        caveats=["unknown_os"],
    )


def log_summary(caps: PlatformCapabilities) -> None:
    """Emit one INFO line summarizing detected capabilities."""
    logger.info(
        "platform: os=%s display=%s hotkeys=%s mouse=%s caveats=%s",
        caps.os_name,
        caps.display_server,
        caps.has_global_hotkeys,
        caps.has_global_mouse_events,
        caps.caveats or "none",
    )
