"""Settings dataclass: validators, atomic save, schema migrations.

These tests target the most security/integrity-sensitive module of the app:
the persistence layer must (a) reject malformed user input gracefully,
(b) never corrupt the on-disk config under crash, (c) survive future schema
changes via the migration registry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pyautoclick.persistence.settings import (
    CURRENT_CONFIG_VERSION,
    Settings,
    migrate_to_current,
)

# ----------------------------------------------------------------------
# load() defaults / missing file
# ----------------------------------------------------------------------


def test_load_returns_defaults_when_no_config_file(tmp_config_dir: Path) -> None:
    """A fresh user environment must not crash; defaults must apply."""
    s = Settings.load()
    assert s.cps == 15, "default cps must be 15"
    assert s.trigger == "button8", "default trigger must be button8"
    assert s.theme == "dark", "default theme must be dark"
    assert s.language is None, "language must be None until first detect"
    assert s.config_version == CURRENT_CONFIG_VERSION


def test_load_returns_defaults_when_config_is_empty(tmp_config_dir, write_config) -> None:
    """An empty JSON object must yield all defaults, not crash."""
    write_config({})
    s = Settings.load()
    assert s.cps == 15, "empty config must yield default cps"


def test_load_returns_defaults_when_config_is_corrupt(tmp_config_dir: Path) -> None:
    """A truncated/malformed JSON file must NOT crash the app."""
    cfg = tmp_config_dir / "config.json"
    cfg.write_text("{ not valid json")
    s = Settings.load()
    assert s.cps == 15, "corrupt JSON must fallback to defaults"


def test_load_returns_defaults_when_config_is_not_a_mapping(tmp_config_dir, write_config) -> None:
    """A JSON array at root must not be accepted as Settings."""
    cfg = tmp_config_dir / "config.json"
    cfg.write_text(json.dumps([1, 2, 3]))
    s = Settings.load()
    assert s.cps == 15, "non-mapping root must fallback to defaults"


# ----------------------------------------------------------------------
# Field-level validators (the heart of CAC40 input hardening)
# ----------------------------------------------------------------------


@pytest.mark.parametrize("bad_value", ["fast", None, [], {}, True, False, 1.5])
def test_load_rejects_non_int_cps(tmp_config_dir, write_config, bad_value) -> None:
    """Any non-int cps must fall back to default 15."""
    write_config({"cps": bad_value})
    s = Settings.load()
    assert s.cps == 15, f"cps={bad_value!r} should fall back to default"


@pytest.mark.parametrize("out_of_range", [-1, 0, 201, 1_000_000])
def test_load_rejects_out_of_range_cps(tmp_config_dir, write_config, out_of_range) -> None:
    """cps must be inside [1, 200]."""
    write_config({"cps": out_of_range})
    s = Settings.load()
    assert s.cps == 15, f"cps={out_of_range} outside [1,200] must fallback"


@pytest.mark.parametrize("good", [1, 15, 50, 100, 200])
def test_load_accepts_valid_cps(tmp_config_dir, write_config, good) -> None:
    """All boundary values inside [1, 200] must be preserved."""
    write_config({"cps": good})
    s = Settings.load()
    assert s.cps == good


@pytest.mark.parametrize("bad", ["button42", "left_extra", "", 8, None, []])
def test_load_rejects_unknown_trigger(tmp_config_dir, write_config, bad) -> None:
    """An unknown trigger key must fall back to default button8."""
    write_config({"trigger": bad})
    s = Settings.load()
    assert s.trigger == "button8", f"trigger={bad!r} should fallback"


@pytest.mark.parametrize("bad", ["super_dark", "auto", None, 1, []])
def test_load_rejects_unknown_theme(tmp_config_dir, write_config, bad) -> None:
    """Theme must be 'dark' or 'light'."""
    write_config({"theme": bad})
    s = Settings.load()
    assert s.theme == "dark", f"theme={bad!r} should fallback"


@pytest.mark.parametrize("bad", ["es-ES", "english", "ZH", 1, [], {}])
def test_load_rejects_unknown_language(tmp_config_dir, write_config, bad) -> None:
    """Language must be None or one of the supported codes."""
    write_config({"language": bad})
    s = Settings.load()
    assert s.language is None, f"language={bad!r} should fallback"


def test_load_accepts_none_language(tmp_config_dir, write_config) -> None:
    """``null`` (None) is a valid value meaning 'auto-detect'."""
    write_config({"language": None})
    s = Settings.load()
    assert s.language is None


@pytest.mark.parametrize("good", ["en", "fr", "es", "ar", "he", "zh"])
def test_load_accepts_supported_languages(tmp_config_dir, write_config, good) -> None:
    write_config({"language": good})
    s = Settings.load()
    assert s.language == good


@pytest.mark.parametrize(
    "bad_positions",
    [
        "not a list",
        {"x": 1},
        [{"x": 1, "y": 2}],  # not a [x, y] pair
        [[1, 2, 3]],  # too many coords
        [[1]],  # too few
        [["1", "2"]],  # str not int
        [[1.5, 2.5]],  # float not int
    ],
)
def test_load_rejects_malformed_positions(tmp_config_dir, write_config, bad_positions) -> None:
    """Positions must be a list of [int, int] pairs."""
    write_config({"auto_positions": bad_positions})
    s = Settings.load()
    assert s.auto_positions == [], f"positions={bad_positions!r} should fallback to []"


def test_load_converts_lists_to_tuples_for_positions(tmp_config_dir, write_config) -> None:
    """JSON has no tuple type; loader must convert [x, y] arrays to tuples."""
    write_config({"auto_positions": [[100, 200], [300, 400]]})
    s = Settings.load()
    assert s.auto_positions == [(100, 200), (300, 400)]
    assert all(isinstance(p, tuple) for p in s.auto_positions), "positions must be tuples"


def test_load_partial_config_keeps_other_defaults(tmp_config_dir, write_config) -> None:
    """A config providing only some keys must keep defaults for the rest."""
    write_config({"cps": 50, "theme": "light"})
    s = Settings.load()
    assert s.cps == 50
    assert s.theme == "light"
    assert s.trigger == "button8", "unspecified field must keep default"
    assert s.hold_enabled is True


def test_load_silently_ignores_unknown_keys(tmp_config_dir, write_config) -> None:
    """Forward compatibility: unknown keys (e.g. from a newer version) must not crash."""
    write_config({"cps": 25, "future_feature_flag": True, "another": [1, 2]})
    s = Settings.load()
    assert s.cps == 25


# ----------------------------------------------------------------------
# Atomic save
# ----------------------------------------------------------------------


def test_save_creates_config_file(tmp_config_dir: Path) -> None:
    s = Settings.load()
    s.cps = 42
    s.save()
    assert (tmp_config_dir / "config.json").exists(), "save must create the file"


def test_save_is_atomic_no_temp_files_left(tmp_config_dir: Path) -> None:
    """A successful save must not leave .config-XXXX.tmp siblings around."""
    s = Settings.load()
    s.cps = 99
    s.save()
    leftovers = [p.name for p in tmp_config_dir.iterdir() if p.name.startswith(".config-")]
    assert leftovers == [], f"atomic save left temp files: {leftovers}"


def test_save_then_load_is_identity(tmp_config_dir: Path) -> None:
    """Roundtrip must preserve exactly every field value."""
    s = Settings.load()
    s.cps = 33
    s.theme = "light"
    s.language = "fr"
    s.auto_positions = [(10, 20), (30, 40)]
    s.hotkey_auto_toggle = "<ctrl>+<alt>+t"
    s.save()

    s2 = Settings.load()
    assert s2 == s, f"roundtrip lost data:\n  saved={s}\n loaded={s2}"


def test_save_overwrites_existing_file(tmp_config_dir: Path) -> None:
    """Saving twice must replace the previous JSON, not append/append."""
    s = Settings.load()
    s.cps = 10
    s.save()
    first_size = (tmp_config_dir / "config.json").stat().st_size

    s.cps = 100
    s.save()
    second_size = (tmp_config_dir / "config.json").stat().st_size

    assert second_size > 0, "second save produced empty file"
    s3 = Settings.load()
    assert s3.cps == 100, "second save must have replaced the file"
    # File size delta should reflect the int width change, not doubling
    assert second_size < first_size * 2, "save appears to have appended, not replaced"


def test_save_preserves_existing_file_on_io_error(tmp_config_dir: Path, monkeypatch) -> None:
    """If save fails mid-write, the previous config.json must remain intact.

    Simulates a disk error during the rename phase.
    """
    s = Settings.load()
    s.cps = 50
    s.save()
    original_bytes = (tmp_config_dir / "config.json").read_bytes()

    # Force os.replace to fail
    def _fail_replace(src, dst):
        raise OSError("simulated disk full")

    monkeypatch.setattr(os, "replace", _fail_replace)

    s.cps = 99
    with pytest.raises(OSError, match="simulated"):
        s.save()

    # Original file must be untouched
    assert (tmp_config_dir / "config.json").read_bytes() == original_bytes
    # No leftover temp files (we still want cleanup on failure)
    leftovers = [p.name for p in tmp_config_dir.iterdir() if p.name.startswith(".config-")]
    assert leftovers == [], f"failed save left temp files: {leftovers}"


# ----------------------------------------------------------------------
# Schema migrations
# ----------------------------------------------------------------------


def test_migrate_v0_to_current_no_op(tmp_config_dir, write_config) -> None:
    """A pre-v1 config (no config_version field) must load via the v0->v1 path."""
    # No config_version key = treated as v0
    write_config({"cps": 25, "theme": "light"})
    s = Settings.load()
    assert s.cps == 25
    assert s.theme == "light"
    assert s.config_version == CURRENT_CONFIG_VERSION


def test_migrate_unknown_future_version_falls_back_to_defaults(
    tmp_config_dir, write_config
) -> None:
    """A config_version > CURRENT must not crash; we attempt best-effort load."""
    # version=999 means "from the future" — no migration registered
    write_config({"config_version": 999, "cps": 50})
    s = Settings.load()
    # Best effort: known fields are still applied
    assert s.cps == 50


def test_migrate_to_current_stamps_version() -> None:
    """``migrate_to_current`` must always end with ``config_version == CURRENT``."""
    data = {"cps": 30}
    migrated = migrate_to_current(data, from_version=0)
    assert migrated["config_version"] == CURRENT_CONFIG_VERSION


# ----------------------------------------------------------------------
# Legacy migration (FR labels -> stable keys)
# ----------------------------------------------------------------------


def test_legacy_french_trigger_label_is_migrated(tmp_config_dir, write_config) -> None:
    """A v0 config with French trigger label must be normalized to the stable key."""
    write_config({"trigger": "Bouton latéral arrière (8)"})
    s = Settings.load()
    assert s.trigger == "button8"


def test_legacy_french_action_label_is_migrated(tmp_config_dir, write_config) -> None:
    write_config({"action": "Clic droit", "auto_action": "Clic milieu"})
    s = Settings.load()
    assert s.action == "right"
    assert s.auto_action == "middle"


# ----------------------------------------------------------------------
# Security: input never reaches the file system unsanitized
# ----------------------------------------------------------------------


def test_load_does_not_evaluate_arbitrary_strings(tmp_config_dir: Path) -> None:
    """A malicious config must NOT execute Python code (basic sanity)."""
    cfg = tmp_config_dir / "config.json"
    cfg.write_text("{\"cps\": \"__import__('os').system('echo pwned')\"}")
    s = Settings.load()
    # Validator rejected the string -> default 15
    assert s.cps == 15


def test_load_handles_unicode_in_hotkeys(tmp_config_dir, write_config) -> None:
    """Unicode in hotkey strings must round-trip safely."""
    write_config({"hotkey_auto_toggle": "<ctrl>+<shift>+é"})
    s = Settings.load()
    # Validator accepts any string for hotkeys (parsing happens in HotkeyManager)
    assert s.hotkey_auto_toggle == "<ctrl>+<shift>+é"
