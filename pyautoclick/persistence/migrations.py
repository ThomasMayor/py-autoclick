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


def _safe_lookup(value: object, table: dict[str, str]) -> str | None:
    """Return ``table[value]`` if ``value`` is a hashable key in ``table``, else None.

    Guards against malicious/malformed configs containing unhashable types
    (lists, dicts) which would otherwise raise ``TypeError`` in ``in``.
    """
    try:
        return table.get(value)  # type: ignore[arg-type]
    except TypeError:
        return None


def migrate_legacy_data(data: dict) -> None:
    """Mutate ``data`` (the raw on-disk dict) in place to upgrade legacy values.

    Must run **before** field-level validation so that legacy strings like
    ``"Bouton latéral arrière (8)"`` are normalized to stable keys before the
    validators reject them as unknown.
    """
    new_trigger = _safe_lookup(data.get("trigger"), LEGACY_TRIGGER_MAP)
    if new_trigger is not None:
        data["trigger"] = new_trigger
    for attr in ("action", "auto_action"):
        new_value = _safe_lookup(data.get(attr), LEGACY_ACTION_MAP)
        if new_value is not None:
            data[attr] = new_value


def migrate_legacy(settings) -> None:
    """Mutate ``settings`` in place to upgrade legacy values (post-validation pass).

    Kept for backward compatibility with callers that already hold a Settings
    instance. New code should prefer :func:`migrate_legacy_data` on the raw
    dict before validation runs.
    """
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
