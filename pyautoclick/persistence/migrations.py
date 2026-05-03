"""Legacy config migrations.

Older versions stored French button labels directly in the config (e.g.
``"trigger": "Bouton latéral arrière (8)"``). We now store stable, language-
agnostic keys (``"button8"``). Migration is best-effort and silent.
"""

from __future__ import annotations

from pyautoclick.core.buttons import ACTION_BUTTONS, TRIGGER_BUTTONS

LEGACY_TRIGGER_MAP = {
    "Bouton latéral arrière (8)": "button8",
    "Bouton latéral avant (9)": "button9",
    "Bouton du milieu": "middle",
    "Bouton droit": "right",
}

LEGACY_ACTION_MAP = {
    "Clic gauche": "left",
    "Clic droit": "right",
    "Clic milieu": "middle",
}


def migrate_legacy(settings) -> None:
    """Mutate ``settings`` in place to upgrade legacy values to current schema."""
    if settings.trigger in LEGACY_TRIGGER_MAP:
        settings.trigger = LEGACY_TRIGGER_MAP[settings.trigger]
    if settings.trigger not in TRIGGER_BUTTONS:
        settings.trigger = "button8"

    for attr in ("action", "auto_action"):
        v = getattr(settings, attr)
        if v in LEGACY_ACTION_MAP:
            setattr(settings, attr, LEGACY_ACTION_MAP[v])
        if getattr(settings, attr) not in ACTION_BUTTONS:
            setattr(settings, attr, "left")

    if not isinstance(settings.auto_positions, list):
        settings.auto_positions = []
