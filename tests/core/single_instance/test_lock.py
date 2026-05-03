"""Single-instance lock tests (the exemplary test from the audit punch list).

Covers the contract:
- The first acquire returns a non-None handle.
- A second acquire while the first is still held returns None.
- Releasing (closing the file / process death) frees the lock.
- ``signal_existing_instance`` returns False when no socket exists.
- Cleanup is idempotent.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from pyautoclick.core.single_instance import (
    acquire_single_instance_lock,
    cleanup_socket,
    signal_existing_instance,
)

pytestmark = pytest.mark.linux_only


def test_acquire_lock_returns_handle_when_free(tmp_config_dir: Path) -> None:
    handle = acquire_single_instance_lock()
    assert handle is not None
    assert (tmp_config_dir / "app.lock").exists()
    handle.close()


def test_acquire_lock_returns_none_when_already_held(tmp_config_dir: Path) -> None:
    first = acquire_single_instance_lock()
    assert first is not None
    try:
        second = acquire_single_instance_lock()
        assert second is None, "second acquire should fail while first holds the lock"
    finally:
        first.close()


def test_lock_released_when_handle_closed(tmp_config_dir: Path) -> None:
    first = acquire_single_instance_lock()
    assert first is not None
    first.close()
    second = acquire_single_instance_lock()
    assert second is not None, "lock should be free after handle close"
    second.close()


def _hold_lock_subprocess(lock_path_str: str, hold_seconds: float) -> None:
    """Helper for the cross-process test."""
    # Re-patch paths in the child since fixtures don't carry over.
    from unittest.mock import patch

    from pyautoclick.core import single_instance as si

    lock_path = Path(lock_path_str)
    with (
        patch.object(si, "LOCK_FILE", lock_path),
        patch.object(si, "CONFIG_DIR", lock_path.parent),
    ):
        h = si.acquire_single_instance_lock()
        if h is None:
            raise SystemExit(1)
        time.sleep(hold_seconds)
        h.close()


def test_lock_blocks_other_process(tmp_config_dir: Path) -> None:
    """The lock is OS-level; another process must observe it as held."""
    lock_path = tmp_config_dir / "app.lock"

    p = multiprocessing.Process(
        target=_hold_lock_subprocess,
        args=(str(lock_path), 0.5),
    )
    p.start()
    # Wait briefly for the child to acquire
    time.sleep(0.1)
    try:
        handle = acquire_single_instance_lock()
        assert handle is None, "other process holds the lock"
    finally:
        p.join(timeout=2)


def test_signal_existing_returns_false_when_no_socket(tmp_config_dir: Path) -> None:
    # Socket file does not exist; no instance to signal.
    assert signal_existing_instance() is False


def test_cleanup_socket_idempotent(tmp_config_dir: Path) -> None:
    # First call: nothing to clean, should not raise.
    cleanup_socket()
    # Create a fake socket file then clean
    sock = tmp_config_dir / "app.sock"
    sock.write_text("")
    cleanup_socket()
    assert not sock.exists()
    # Second call: gone but no raise.
    cleanup_socket()
