"""Schema migrations + legacy value normalization."""

from __future__ import annotations

from pyautoclick.persistence.migrations import (
    LEGACY_ACTION_MAP,
    LEGACY_TRIGGER_MAP,
    _safe_lookup,
    migrate_legacy_data,
)
from pyautoclick.persistence.settings import (
    CURRENT_CONFIG_VERSION,
    migrate_to_current,
)

# ----------------------------------------------------------------------
# _safe_lookup: defensive against unhashable types
# ----------------------------------------------------------------------


class TestSafeLookup:
    def test_returns_value_for_known_key(self):
        assert _safe_lookup("Clic gauche", LEGACY_ACTION_MAP) == "left"

    def test_returns_none_for_unknown_key(self):
        assert _safe_lookup("Unknown", LEGACY_ACTION_MAP) is None

    def test_returns_none_for_unhashable_list(self):
        """A list value must not crash with TypeError; just return None."""
        assert _safe_lookup([1, 2], LEGACY_TRIGGER_MAP) is None

    def test_returns_none_for_unhashable_dict(self):
        assert _safe_lookup({"x": 1}, LEGACY_TRIGGER_MAP) is None

    def test_returns_none_for_none(self):
        assert _safe_lookup(None, LEGACY_TRIGGER_MAP) is None


# ----------------------------------------------------------------------
# migrate_legacy_data: mutate raw dict
# ----------------------------------------------------------------------


class TestMigrateLegacyData:
    def test_translates_french_trigger_label(self):
        data = {"trigger": "Bouton latéral arrière (8)"}
        migrate_legacy_data(data)
        assert data["trigger"] == "button8"

    def test_translates_french_action_label(self):
        data = {"action": "Clic droit", "auto_action": "Clic milieu"}
        migrate_legacy_data(data)
        assert data["action"] == "right"
        assert data["auto_action"] == "middle"

    def test_passes_through_unknown_trigger(self):
        """Unknown values must be left alone (validator handles them later)."""
        data = {"trigger": "future_button"}
        migrate_legacy_data(data)
        assert data["trigger"] == "future_button"

    def test_passes_through_already_stable_keys(self):
        data = {"trigger": "button8", "action": "left"}
        migrate_legacy_data(data)
        assert data["trigger"] == "button8"
        assert data["action"] == "left"

    def test_no_op_on_empty_dict(self):
        data: dict = {}
        migrate_legacy_data(data)
        assert data == {}

    def test_unhashable_trigger_does_not_crash(self):
        """A malformed config with a list as trigger must not raise."""
        data = {"trigger": [1, 2, 3]}
        migrate_legacy_data(data)
        # Value left as-is; validator will reject and fall back
        assert data["trigger"] == [1, 2, 3]


# ----------------------------------------------------------------------
# migrate_to_current: schema version stamping
# ----------------------------------------------------------------------


class TestMigrateToCurrent:
    def test_stamps_current_version(self):
        data = {"cps": 30}
        out = migrate_to_current(data, from_version=0)
        assert out["config_version"] == CURRENT_CONFIG_VERSION

    def test_v0_to_v1_is_noop_on_known_fields(self):
        """v0 -> v1 just stamps the version; no key renames."""
        data = {"cps": 30, "theme": "light"}
        out = migrate_to_current(data, from_version=0)
        assert out["cps"] == 30
        assert out["theme"] == "light"

    def test_already_at_current_version_is_noop(self):
        """If config_version == CURRENT, no migrations run."""
        data = {"cps": 30, "config_version": CURRENT_CONFIG_VERSION}
        out = migrate_to_current(data, from_version=CURRENT_CONFIG_VERSION)
        assert out["cps"] == 30
        assert out["config_version"] == CURRENT_CONFIG_VERSION

    def test_unknown_future_version_is_stamped_to_current(self):
        """A 'from-the-future' version is best-effort: keep data, stamp version.

        We log a warning but don't crash, so the user can still launch the app
        after a downgrade.
        """
        data = {"cps": 30, "config_version": 9999}
        out = migrate_to_current(data, from_version=9999)
        assert out["config_version"] == CURRENT_CONFIG_VERSION

    def test_stamping_does_not_destroy_other_fields(self):
        data = {"cps": 30, "trigger": "button8", "language": "fr"}
        out = migrate_to_current(data, from_version=0)
        assert out["cps"] == 30
        assert out["trigger"] == "button8"
        assert out["language"] == "fr"
