"""Notifications dispatcher: per-OS backend + silent no-op when missing."""

from __future__ import annotations

from unittest.mock import patch

from pyautoclick.services.notifications import (
    _notify_linux,
    _notify_macos,
    _notify_windows,
    notify,
)


class TestLinuxBackend:
    def test_returns_false_when_notify_send_missing(self):
        with patch("shutil.which", return_value=None):
            assert _notify_linux("title", "msg") is False

    def test_calls_notify_send_when_available(self):
        with patch("shutil.which", return_value="/usr/bin/notify-send"):
            with patch("subprocess.Popen") as popen:
                ok = _notify_linux("My Title", "My Message")
        assert ok is True
        popen.assert_called_once()
        args = popen.call_args.args[0]
        assert args[0] == "notify-send"
        assert "My Title" in args
        assert "My Message" in args

    def test_oserror_is_silent(self):
        """A subprocess launch failure must not raise."""
        with patch("shutil.which", return_value="/usr/bin/notify-send"):
            with patch("subprocess.Popen", side_effect=OSError("boom")):
                ok = _notify_linux("t", "m")
        assert ok is False


class TestMacosBackend:
    def test_returns_false_when_osascript_missing(self):
        with patch("shutil.which", return_value=None):
            assert _notify_macos("t", "m") is False

    def test_escapes_double_quotes_in_message(self):
        """Quote injection must be neutralized."""
        with patch("shutil.which", return_value="/usr/bin/osascript"):
            with patch("subprocess.Popen") as popen:
                _notify_macos('Title with "quote"', 'Msg with "quote"')
        script = popen.call_args.args[0][2]
        # Escaped form
        assert '\\"quote\\"' in script


class TestWindowsBackend:
    def test_returns_false_when_powershell_missing(self):
        with patch("shutil.which", return_value=None):
            assert _notify_windows("t", "m") is False

    def test_escapes_single_quotes(self):
        """PowerShell uses single-quoted strings; quotes inside must be doubled."""
        with patch("shutil.which", return_value="/usr/bin/powershell"):
            with patch("subprocess.Popen") as popen:
                _notify_windows("Bob's title", "It's a message")
        ps_script = popen.call_args.args[0][-1]
        assert "Bob''s title" in ps_script
        assert "It''s a message" in ps_script


class TestDispatcher:
    def test_dispatches_to_linux_backend(self):
        with patch("sys.platform", "linux"):
            with patch("pyautoclick.services.notifications._notify_linux") as backend:
                notify("t", "m")
        backend.assert_called_once_with("t", "m")

    def test_dispatches_to_macos_backend(self):
        with patch("sys.platform", "darwin"):
            with patch("pyautoclick.services.notifications._notify_macos") as backend:
                notify("t", "m")
        backend.assert_called_once_with("t", "m")

    def test_dispatches_to_windows_backend(self):
        with patch("sys.platform", "win32"):
            with patch("pyautoclick.services.notifications._notify_windows") as backend:
                notify("t", "m")
        backend.assert_called_once_with("t", "m")

    def test_unknown_platform_is_silent(self):
        """An unsupported OS must not raise; just log debug."""
        with patch("sys.platform", "freebsd"):
            # No backend called, no exception
            notify("t", "m")  # Should not raise
