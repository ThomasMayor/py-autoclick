"""Mouse button identifiers.

Stable language-agnostic keys -> pynput Button objects.
Combobox labels are resolved via the i18n layer (translation keys
``trigger_<key>`` and ``action_<key>``).
"""

from __future__ import annotations

from pynput.mouse import Button

TRIGGER_KEYS = ["button8", "button9", "middle", "right"]
TRIGGER_BUTTONS = {
    "button8": Button.button8,
    "button9": Button.button9,
    "middle": Button.middle,
    "right": Button.right,
}

ACTION_KEYS = ["left", "right", "middle"]
ACTION_BUTTONS = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}
