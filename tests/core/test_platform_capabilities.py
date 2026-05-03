"""Platform capability detection: OS + display server."""

from __future__ import annotations

import os
from unittest.mock import patch

from pyautoclick.core.platform_capabilities import (
    PlatformCapabilities,
    detect,
    log_summary,
)


class TestDetect:
    def test_windows(self):
        with patch("sys.platform", "win32"):
            caps = detect()
        assert caps.os_name == "windows"
        assert caps.display_server == "windows"
        assert caps.has_global_hotkeys is True
        assert caps.has_global_mouse_events is True
        assert caps.caveats == []

    def test_macos(self):
        with patch("sys.platform", "darwin"):
            caps = detect()
        assert caps.os_name == "macos"
        assert caps.display_server == "macos"
        assert caps.has_global_hotkeys is True
        assert "macos_accessibility_required" in caps.caveats

    def test_linux_x11_via_xdg(self):
        with (
            patch("sys.platform", "linux"),
            patch.dict(
                os.environ,
                {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"},
                clear=True,
            ),
        ):
            caps = detect()
        assert caps.os_name == "linux"
        assert caps.display_server == "x11"
        assert caps.has_global_hotkeys is True
        assert caps.caveats == []

    def test_linux_x11_via_display_only(self):
        """If XDG_SESSION_TYPE missing but DISPLAY is set, treat as x11."""
        with patch("sys.platform", "linux"):
            with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
                caps = detect()
        assert caps.display_server == "x11"

    def test_linux_wayland_via_xdg(self):
        with (
            patch("sys.platform", "linux"),
            patch.dict(
                os.environ,
                {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"},
                clear=True,
            ),
        ):
            caps = detect()
        assert caps.display_server == "wayland"
        assert caps.has_global_hotkeys is False, (
            "Wayland blocks global keyboard hotkeys for security; "
            "this is the conservative assumption"
        )
        assert "wayland_hotkeys_blocked" in caps.caveats

    def test_linux_wayland_via_wayland_display_only(self):
        """If XDG missing but WAYLAND_DISPLAY set, treat as wayland."""
        with (
            patch("sys.platform", "linux"),
            patch.dict(
                os.environ,
                {"WAYLAND_DISPLAY": "wayland-0"},
                clear=True,
            ),
        ):
            caps = detect()
        assert caps.display_server == "wayland"

    def test_linux_unknown_display_server(self):
        """No XDG, no DISPLAY, no WAYLAND_DISPLAY -> conservative unknown."""
        with patch("sys.platform", "linux"), patch.dict(os.environ, {}, clear=True):
            caps = detect()
        assert caps.display_server == "unknown"
        assert caps.has_global_hotkeys is False
        assert "unknown_display_server" in caps.caveats

    def test_unknown_os(self):
        with patch("sys.platform", "freebsd"), patch.dict(os.environ, {}, clear=True):
            caps = detect()
        assert caps.os_name == "freebsd"
        assert caps.display_server == "unknown"
        assert caps.has_global_hotkeys is False
        assert "unknown_os" in caps.caveats


class TestLogSummary:
    def test_log_summary_does_not_crash(self, caplog):
        """Sanity: log_summary must produce one INFO line and not raise."""
        import logging

        caps = PlatformCapabilities(
            os_name="linux",
            display_server="x11",
            has_global_hotkeys=True,
            has_global_mouse_events=True,
            caveats=[],
        )
        with caplog.at_level(logging.INFO, logger="pyautoclick.core.platform_capabilities"):
            log_summary(caps)
        assert any("platform:" in r.message for r in caplog.records)
