"""Shared pytest fixtures."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest


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
