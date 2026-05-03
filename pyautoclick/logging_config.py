"""Centralized logging setup.

Call :func:`configure_logging` once at application startup. After that,
modules obtain their logger via ``logger = logging.getLogger(__name__)``
without further configuration.

Log level can be overridden at runtime via the ``PYAUTOCLICK_LOG_LEVEL``
environment variable (e.g. ``DEBUG``, ``INFO``, ``WARNING``). Defaults
to ``INFO``.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pyautoclick.paths import CONFIG_DIR

LOG_FILE = CONFIG_DIR / "pyautoclick.log"

_DEFAULT_FMT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_ENV_VAR = "PYAUTOCLICK_LOG_LEVEL"

_configured = False


def configure_logging(*, log_to_file: bool = True) -> None:
    """Configure the root logger. Idempotent — safe to call multiple times.

    Two handlers when ``log_to_file`` is true:
    - stderr (always)
    - rotating file ``~/.config/autoclicker/pyautoclick.log`` (1 MB x 3)
    """
    global _configured
    if _configured:
        return

    level_name = os.environ.get(_ENV_VAR, "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(_DEFAULT_FMT, datefmt=_DATE_FMT)

    handlers: list[logging.Handler] = []

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    handlers.append(stderr_handler)

    if log_to_file:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=1_048_576,    # 1 MiB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except OSError:
            # File logging is best-effort; never block startup on it.
            pass

    root = logging.getLogger()
    root.setLevel(level)
    # Replace any pre-existing handlers (e.g. from previous configure call,
    # or accidental basicConfig elsewhere)
    root.handlers.clear()
    for h in handlers:
        root.addHandler(h)

    # Quiet down very chatty third-party loggers if they appear later
    logging.getLogger("pynput").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    _configured = True


def get_log_file() -> Path:
    return LOG_FILE
