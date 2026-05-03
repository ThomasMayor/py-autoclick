"""Typed, validated settings dataclass with atomic JSON persistence.

Loading is fault-tolerant: invalid fields silently fall back to their default
(after logging a warning). The on-disk format carries a ``config_version`` so
future schema changes can apply migrations on load.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal, get_args, get_origin

from pyautoclick.core.buttons import ACTION_BUTTONS, TRIGGER_BUTTONS
from pyautoclick.paths import CONFIG_DIR, CONFIG_FILE
from pyautoclick.persistence.migrations import migrate_legacy

logger = logging.getLogger(__name__)

CURRENT_CONFIG_VERSION = 1

LanguageCode = Literal["en", "fr"]
ThemeName = Literal["dark", "light"]

Position = tuple[int, int]


@dataclass
class Settings:
    # --- versioning (persisted but not user-facing) ---
    config_version: int = CURRENT_CONFIG_VERSION

    # --- mode maintenu ---
    hold_enabled: bool = True
    trigger: str = "button8"
    action: str = "left"
    cps: int = 15
    hold_jitter_ms: int = 0

    # --- mode automatique ---
    auto_action: str = "left"
    auto_interval_ms: int = 100
    auto_press_ms: int = 10
    auto_jitter_ms: int = 0
    auto_click_limit: int = 0
    auto_use_positions: bool = False
    auto_positions: list[Position] = field(default_factory=list)

    # --- raccourcis (format pynput, "" = désactivé) ---
    hotkey_auto_toggle: str = "<ctrl>+<shift>+e"
    hotkey_auto_momentary: str = ""
    hotkey_panic: str = "<ctrl>+<shift>+x"

    # --- divers ---
    notify_enabled: bool = True
    theme: ThemeName = "dark"
    language: LanguageCode | None = None    # None = détecter au premier lancement

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> Settings:
        """Read ``CONFIG_FILE`` if present. Invalid values fall back to defaults."""
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.info("no config file found, using defaults")
            return cls()
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("config file unreadable (%s); using defaults", exc)
            return cls()

        if not isinstance(data, dict):
            logger.warning("config root is not a mapping; using defaults")
            return cls()

        # Apply on-disk migrations BEFORE field-by-field validation so version
        # bumps can rename/move keys.
        version = data.get("config_version", 0)
        data = migrate_to_current(data, from_version=version)

        s = cls()
        for f_def in fields(cls):
            if f_def.name in data:
                _assign_validated(s, f_def.name, data[f_def.name])

        # Run legacy value-level migration (FR labels -> stable keys)
        migrate_legacy(s)
        return s

    def save(self) -> None:
        """Atomically write to ``CONFIG_FILE``.

        Writes to a sibling temp file then ``os.replace()`` so a crash mid-write
        cannot corrupt the existing config.
        """
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # NamedTemporaryFile in same dir to keep replace atomic on POSIX
        fd, tmp_path = tempfile.mkstemp(
            prefix=".config-", suffix=".tmp", dir=str(CONFIG_DIR)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, CONFIG_FILE)
        except OSError:
            logger.exception("failed to save settings to %s", CONFIG_FILE)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


# ----------------------------------------------------------------------
# Field-level validation
# ----------------------------------------------------------------------

# Per-field validators. Each takes the raw value and returns the validated
# value, or raises ValueError. The default is used when a validator raises.
_INT_BOUNDS = {
    "cps": (1, 200),
    "hold_jitter_ms": (0, 10_000),
    "auto_interval_ms": (1, 600_000),
    "auto_press_ms": (0, 60_000),
    "auto_jitter_ms": (0, 60_000),
    "auto_click_limit": (0, 10_000_000),
    "config_version": (0, 1_000_000),
}

_VALID_LANGUAGES = set(get_args(LanguageCode))
_VALID_THEMES = set(get_args(ThemeName))


def _assign_validated(s: Settings, name: str, raw: Any) -> None:
    try:
        value = _validate(name, raw)
    except (TypeError, ValueError) as exc:
        default = getattr(Settings(), name)
        logger.warning(
            "invalid value for %r in config (%s); falling back to default %r",
            name, exc, default,
        )
        return  # default already in place from cls() init
    setattr(s, name, value)


def _validate(name: str, raw: Any) -> Any:  # noqa: PLR0911 — exhaustive switch
    if name == "trigger":
        if raw not in TRIGGER_BUTTONS:
            raise ValueError(f"unknown trigger key: {raw!r}")
        return raw

    if name in ("action", "auto_action"):
        if raw not in ACTION_BUTTONS:
            raise ValueError(f"unknown action key: {raw!r}")
        return raw

    if name in _INT_BOUNDS:
        lo, hi = _INT_BOUNDS[name]
        if not isinstance(raw, int) or isinstance(raw, bool):
            raise TypeError(f"expected int, got {type(raw).__name__}")
        if not (lo <= raw <= hi):
            raise ValueError(f"out of range [{lo}..{hi}]: {raw}")
        return raw

    if name in ("hold_enabled", "auto_use_positions", "notify_enabled"):
        if not isinstance(raw, bool):
            raise TypeError(f"expected bool, got {type(raw).__name__}")
        return raw

    if name in ("hotkey_auto_toggle", "hotkey_auto_momentary", "hotkey_panic"):
        if not isinstance(raw, str):
            raise TypeError(f"expected str, got {type(raw).__name__}")
        return raw

    if name == "theme":
        if raw not in _VALID_THEMES:
            raise ValueError(f"unknown theme: {raw!r}")
        return raw

    if name == "language":
        if raw is None:
            return None
        if raw not in _VALID_LANGUAGES:
            raise ValueError(f"unknown language: {raw!r}")
        return raw

    if name == "auto_positions":
        if not isinstance(raw, list):
            raise TypeError(f"expected list, got {type(raw).__name__}")
        cleaned: list[Position] = []
        for item in raw:
            if not isinstance(item, list | tuple) or len(item) != 2:
                raise ValueError(f"position must be [x, y], got {item!r}")
            x, y = item
            if not isinstance(x, int) or not isinstance(y, int):
                raise TypeError(f"position coords must be int, got {item!r}")
            cleaned.append((x, y))
        return cleaned

    raise ValueError(f"no validator for field {name!r}")


# ----------------------------------------------------------------------
# Schema migrations
# ----------------------------------------------------------------------

def migrate_to_current(data: dict[str, Any], *, from_version: int) -> dict[str, Any]:
    """Apply schema migrations from ``from_version`` to ``CURRENT_CONFIG_VERSION``.

    Each migration is an in-place dict transformation. Adding new fields with
    safe defaults requires NO migration — the dataclass falls back to defaults.
    Migrations are only needed when renaming, moving, or removing keys.
    """
    version = from_version
    while version < CURRENT_CONFIG_VERSION:
        migration = _MIGRATIONS.get(version)
        if migration is None:
            logger.warning(
                "no migration registered from v%d to v%d; relying on defaults",
                version, version + 1,
            )
            break
        logger.info("migrating config v%d -> v%d", version, version + 1)
        data = migration(data)
        version += 1
    data["config_version"] = CURRENT_CONFIG_VERSION
    return data


def _migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """v0 (no config_version field) -> v1: just stamp the version."""
    return data


# Map of source version -> migration function.
# Add entries here as the schema evolves (rename / move / remove keys).
# Adding new fields with safe defaults requires NO migration: the dataclass
# initializer fills them in.
_MIGRATIONS: dict[int, Any] = {
    0: _migrate_v0_to_v1,
}
