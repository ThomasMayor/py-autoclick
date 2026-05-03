"""Logging configuration: handlers, level override, idempotency."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from pyautoclick import logging_config


@pytest.fixture(autouse=True)
def _reset_state(tmp_path: Path):
    """Each test starts with a clean root logger and idempotency flag."""
    # Save current state
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_configured = logging_config._configured

    # Redirect log file to a temp location and reset
    with patch.object(logging_config, "CONFIG_DIR", tmp_path):
        with patch.object(logging_config, "LOG_FILE", tmp_path / "test.log"):
            logging_config._configured = False
            root.handlers.clear()
            yield

    # Restore
    root.handlers = saved_handlers
    root.level = saved_level
    logging_config._configured = saved_configured


def test_configure_logging_installs_handlers(tmp_path: Path) -> None:
    logging_config.configure_logging()
    root = logging.getLogger()
    assert len(root.handlers) >= 1, "at least stderr handler expected"


def test_configure_logging_creates_log_file(tmp_path: Path) -> None:
    logging_config.configure_logging()
    logging.getLogger("test").info("hello")
    # File handler may buffer; force flush
    for h in logging.getLogger().handlers:
        h.flush()
    assert (tmp_path / "test.log").exists()


def test_configure_logging_is_idempotent() -> None:
    """Calling configure_logging() twice must not duplicate handlers."""
    logging_config.configure_logging()
    n1 = len(logging.getLogger().handlers)
    logging_config.configure_logging()
    n2 = len(logging.getLogger().handlers)
    assert n1 == n2, f"second call added {n2 - n1} extra handler(s)"


def test_default_log_level_is_info() -> None:
    with patch.dict("os.environ", {}, clear=False):
        # Ensure env var is not set
        import os

        os.environ.pop("PYAUTOCLICK_LOG_LEVEL", None)
        logging_config.configure_logging()
    assert logging.getLogger().level == logging.INFO


def test_env_var_overrides_log_level() -> None:
    import os

    with patch.dict(os.environ, {"PYAUTOCLICK_LOG_LEVEL": "DEBUG"}):
        logging_config.configure_logging()
    assert logging.getLogger().level == logging.DEBUG


def test_invalid_env_var_falls_back_to_info() -> None:
    """An unknown level name must not crash; default to INFO."""
    import os

    with patch.dict(os.environ, {"PYAUTOCLICK_LOG_LEVEL": "BANANA"}):
        logging_config.configure_logging()
    assert logging.getLogger().level == logging.INFO


def test_log_to_file_disabled_skips_file_handler(tmp_path: Path) -> None:
    """log_to_file=False must not create a file handler."""
    logging_config.configure_logging(log_to_file=False)
    file_handlers = [h for h in logging.getLogger().handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers == [], "file handler should be skipped"


def test_pynput_logger_quieted() -> None:
    """Third-party loggers must not flood our output."""
    logging_config.configure_logging()
    assert logging.getLogger("pynput").level == logging.WARNING


def test_get_log_file_returns_path() -> None:
    p = logging_config.get_log_file()
    assert isinstance(p, Path)


def test_log_file_io_error_does_not_block_startup(tmp_path: Path) -> None:
    """If the log file cannot be created, startup must continue (stderr only)."""
    bad_dir = tmp_path / "nonexistent" / "deeply" / "nested"
    with patch.object(logging_config, "CONFIG_DIR", bad_dir):
        with patch.object(logging_config, "LOG_FILE", bad_dir / "test.log"):
            with patch("os.makedirs", side_effect=OSError("permission denied")):
                # Should not raise even with broken filesystem
                logging_config.configure_logging()
    # stderr handler still present
    assert len(logging.getLogger().handlers) >= 1
