"""Modal dialog that captures a keyboard combination from the user.

Strings are injected by the caller (i18n stays out of UI widgets).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pyautoclick.ui.constants import CAPTURE_DIALOG_GEOMETRY, CAPTURE_DIALOG_PADDING

# Mapping tk keysym -> pynput token
_KEYSYM_MAP = {
    "space": "<space>",
    "Return": "<enter>",
    "Escape": "<esc>",
    "Tab": "<tab>",
    "BackSpace": "<backspace>",
    "Delete": "<delete>",
    "Insert": "<insert>",
    "Home": "<home>",
    "End": "<end>",
    "Prior": "<page_up>",
    "Next": "<page_down>",
    "Left": "<left>",
    "Right": "<right>",
    "Up": "<up>",
    "Down": "<down>",
    "Caps_Lock": "<caps_lock>",
    "Num_Lock": "<num_lock>",
    "Print": "<print_screen>",
    "Pause": "<pause>",
}
for _i in range(1, 25):
    _KEYSYM_MAP[f"F{_i}"] = f"<f{_i}>"

_MODIFIER_KEYSYMS = {
    "Control_L",
    "Control_R",
    "Shift_L",
    "Shift_R",
    "Alt_L",
    "Alt_R",
    "Super_L",
    "Super_R",
    "Meta_L",
    "Meta_R",
}


def _keysym_to_token(keysym: str) -> str | None:
    if keysym in _KEYSYM_MAP:
        return _KEYSYM_MAP[keysym]
    if len(keysym) == 1:
        return keysym.lower()
    return None


def capture_hotkey_dialog(
    parent, on_done, *, title: str, prompt: str, in_progress_tpl: str, unknown_tpl: str
) -> None:
    """Open a modal dialog. Calls ``on_done(combo_str | None)`` when finished."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry(CAPTURE_DIALOG_GEOMETRY)
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()

    label = ttk.Label(win, text=prompt, anchor="center", font=("", 10), justify="center")
    label.pack(
        fill="both", expand=True, padx=CAPTURE_DIALOG_PADDING[0], pady=CAPTURE_DIALOG_PADDING[1]
    )

    state = {"done": False}

    def finish(combo):
        if state["done"]:
            return
        state["done"] = True
        win.destroy()
        on_done(combo)

    def on_key(event):
        keysym = event.keysym
        if keysym == "Escape":
            finish(None)
            return
        mods = []
        if event.state & 0x4:
            mods.append("<ctrl>")
        if event.state & 0x1:
            mods.append("<shift>")
        if event.state & 0x8:
            mods.append("<alt>")
        if event.state & 0x40:
            mods.append("<cmd>")
        if keysym in _MODIFIER_KEYSYMS:
            label.config(text=in_progress_tpl.format(x="+".join(mods)))
            return
        token = _keysym_to_token(keysym)
        if token is None:
            label.config(text=unknown_tpl.format(x=keysym))
            return
        finish("+".join([*mods, token]))

    win.bind("<Key>", on_key)
    win.protocol("WM_DELETE_WINDOW", lambda: finish(None))
    win.focus_force()
