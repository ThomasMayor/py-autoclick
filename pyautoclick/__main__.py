"""Entry point: ``python -m pyautoclick`` or via the ``pyautoclick`` script."""

from __future__ import annotations

import logging
import signal
import sys
import tkinter as tk
from tkinter import messagebox
from types import FrameType

from pyautoclick.core.platform_capabilities import detect as detect_platform
from pyautoclick.core.platform_capabilities import log_summary as log_platform
from pyautoclick.core.single_instance import (
    acquire_single_instance_lock,
    signal_existing_instance,
    start_focus_server,
)
from pyautoclick.i18n import LANGUAGES, detect_system_language, t
from pyautoclick.logging_config import configure_logging
from pyautoclick.paths import ICON_PATH
from pyautoclick.persistence.settings import Settings
from pyautoclick.ui.app import App
from pyautoclick.ui.theme import bring_to_front

logger = logging.getLogger(__name__)


def _show_already_running_dialog() -> None:
    """Best-effort localized warning before exiting (used as a fallback)."""
    try:
        s = Settings.load()
        lang = s.language or detect_system_language()
    except (OSError, ValueError):
        lang = detect_system_language()
    if lang not in LANGUAGES:
        lang = "en"
    root = tk.Tk()
    root.withdraw()
    messagebox.showwarning(t("app_title", lang), t("instance_already_running", lang))
    root.destroy()


def main() -> None:
    configure_logging()
    logger.info("py-autoclick starting up")
    capabilities = detect_platform()
    log_platform(capabilities)

    # Single-instance enforcement
    lock = acquire_single_instance_lock()
    if lock is None:
        logger.info("another instance already running")
        if signal_existing_instance():
            logger.info("focus request delivered to existing instance, exiting")
            sys.exit(0)
        logger.warning("existing instance is unreachable (zombie?); showing dialog")
        _show_already_running_dialog()
        sys.exit(0)

    root = tk.Tk(className="PyAutoClick")

    try:
        icon = tk.PhotoImage(file=str(ICON_PATH))
        root.iconphoto(True, icon)
        root._icon_ref = icon  # keep ref to avoid GC
    except tk.TclError:
        logger.warning("could not load window icon from %s", ICON_PATH, exc_info=True)

    app = App(root, capabilities=capabilities)
    # Listen for second-instance focus requests (run on socket thread,
    # marshaled to UI thread via root.after)
    start_focus_server(lambda: root.after(0, lambda: bring_to_front(root)))

    # SIGINT (Ctrl+C in terminal) and SIGTERM (kill / logout) trigger a
    # clean shutdown via the existing WM_DELETE_WINDOW handler.
    def _signal_handler(signum: int, _frame: FrameType | None) -> None:
        name = signal.Signals(signum).name
        logger.info("received %s, requesting graceful shutdown", name)
        # Tk handlers must run on the main thread; root.after schedules safely
        root.after(0, app._on_close)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("UI ready, entering mainloop")
    try:
        root.mainloop()
    finally:
        logger.info("mainloop exited cleanly")


if __name__ == "__main__":
    main()
