"""Single instance enforcement: cross-platform lock + IPC for focus.

Backends:
- POSIX (Linux, macOS): ``fcntl.flock`` exclusive lock + Unix-domain socket
- Windows: ``msvcrt.locking`` exclusive lock + TCP loopback socket on a
  port written next to the lock file

The public API (``acquire_single_instance_lock``, ``signal_existing_instance``,
``start_focus_server``, ``cleanup_socket``) is identical on every platform.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
from typing import IO, Callable

from pyautoclick.paths import CONFIG_DIR, LOCK_FILE, SOCKET_FILE

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_PORT_FILE = CONFIG_DIR / "app.port"   # Windows-only: holds the loopback port


# ----------------------------------------------------------------------
# Lock
# ----------------------------------------------------------------------

if _IS_WINDOWS:
    import msvcrt

    def acquire_single_instance_lock() -> IO[str] | None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        f = open(LOCK_FILE, "w")
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            return f
        except OSError:
            f.close()
            return None
else:
    import fcntl

    def acquire_single_instance_lock() -> IO[str] | None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        f = open(LOCK_FILE, "w")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except BlockingIOError:
            f.close()
            return None


# ----------------------------------------------------------------------
# IPC: focus request channel
# ----------------------------------------------------------------------

def _make_server_socket() -> tuple[socket.socket, str | int]:
    """Create the IPC server socket. Returns (sock, identifier).

    On POSIX, identifier is the path to the Unix socket.
    On Windows, identifier is the loopback port number.
    """
    if _IS_WINDOWS:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))   # OS picks a free port
        port = srv.getsockname()[1]
        _PORT_FILE.write_text(str(port))
        return srv, port

    try:
        SOCKET_FILE.unlink()
    except (FileNotFoundError, OSError):
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(SOCKET_FILE))
    return srv, str(SOCKET_FILE)


def _connect_to_existing(timeout: float = 1.0) -> socket.socket | None:
    """Open a client socket to the running instance, or return None."""
    if _IS_WINDOWS:
        try:
            port = int(_PORT_FILE.read_text())
        except (FileNotFoundError, OSError, ValueError):
            return None
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            return s
        except OSError:
            s.close()
            return None

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(str(SOCKET_FILE))
        return s
    except (FileNotFoundError, ConnectionRefusedError, OSError):
        s.close()
        return None


def signal_existing_instance() -> bool:
    """Ask the running instance to come to the foreground.

    Returns ``True`` if the request was delivered, ``False`` otherwise.
    """
    s = _connect_to_existing()
    if s is None:
        return False
    try:
        s.send(b"focus\n")
    except OSError:
        return False
    finally:
        s.close()
    return True


def start_focus_server(on_focus_request: Callable[[], None]) -> socket.socket | None:
    """Start the IPC server. Each connection invokes ``on_focus_request``."""
    try:
        srv, _ident = _make_server_socket()
    except OSError:
        logger.exception("failed to bind focus IPC server")
        return None
    srv.listen(5)

    def loop() -> None:
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                break
            try:
                conn.recv(64)
            except OSError:
                pass
            conn.close()
            try:
                on_focus_request()
            except Exception:    # never let a UI callback kill the listener
                logger.exception("on_focus_request callback raised")

    threading.Thread(
        target=loop, name="single-instance-server", daemon=True,
    ).start()
    return srv


def cleanup_socket() -> None:
    """Remove the on-disk artefacts left by the IPC server."""
    if _IS_WINDOWS:
        try:
            _PORT_FILE.unlink()
        except (FileNotFoundError, OSError):
            pass
        return
    try:
        SOCKET_FILE.unlink()
    except (FileNotFoundError, OSError):
        pass
