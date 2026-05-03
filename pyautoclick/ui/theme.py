"""Theme application + listbox theming + bring-to-front helper."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.ui.colors import (
    ACCENT_BLUE,
    DARK_BG,
    DARK_FG,
    LIGHT_BG,
    LIGHT_FG,
    SELECTION_FG,
)
from pyautoclick.ui.constants import TOPMOST_FLASH_MS


def apply_theme(name: str) -> None:
    """Apply a theme to the global ttk style. Falls back to ``clam`` if sv-ttk absent."""
    try:
        import sv_ttk
        sv_ttk.set_theme("dark" if name == "dark" else "light")
    except ImportError:
        try:
            style = ttk.Style()
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass


def theme_listbox(lb: tk.Listbox, theme_name: str) -> None:
    """Align a tk.Listbox (non-ttk) on the active ttk theme colors."""
    style = ttk.Style()
    is_dark = theme_name == "dark"
    fb_bg = DARK_BG if is_dark else LIGHT_BG
    fb_fg = DARK_FG if is_dark else LIGHT_FG
    bg = (style.lookup("TEntry", "fieldbackground")
          or style.lookup("TFrame", "background")
          or fb_bg)
    fg = (style.lookup("TEntry", "foreground")
          or style.lookup("TLabel", "foreground")
          or fb_fg)
    sel_bg = style.lookup("Accent.TButton", "background") or ACCENT_BLUE
    lb.configure(
        background=bg, foreground=fg,
        selectbackground=sel_bg, selectforeground=SELECTION_FG,
        highlightbackground=bg, highlightcolor=sel_bg,
    )


def bring_to_front(root: tk.Tk) -> None:
    """Raise + focus + brief topmost flash. Safe if root is destroyed."""
    try:
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(TOPMOST_FLASH_MS, lambda: root.attributes("-topmost", False))
        root.focus_force()
    except tk.TclError:
        pass
