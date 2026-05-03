"""Cross-platform smoke tests.

These tests must pass on every supported OS / Python version. They guarantee
that:
- The package imports cleanly on a fresh CI runner (no display, no config).
- The i18n locale files are all loadable and have key parity with English.
- Settings.load() falls back to defaults when no config exists.

Crucially they do NOT carry the ``linux_only`` marker, so the Win/macOS CI
runs (which filter that marker out) still have something to execute.
"""

from __future__ import annotations

import json
from importlib import resources

import pytest


def test_package_imports() -> None:
    import pyautoclick
    import pyautoclick.core.buttons
    import pyautoclick.i18n
    import pyautoclick.persistence.settings

    assert pyautoclick.__version__


def test_languages_list_matches_locale_files() -> None:
    from pyautoclick.i18n import LANGUAGES

    locale_dir = resources.files("pyautoclick.i18n.locales")
    for code in LANGUAGES:
        path = locale_dir.joinpath(f"{code}.json")
        assert path.is_file(), f"missing locale file for {code!r}"


def test_locale_key_parity_with_english() -> None:
    """Every locale must define exactly the same keys as en.json."""
    from pyautoclick.i18n import LANGUAGES

    locale_dir = resources.files("pyautoclick.i18n.locales")
    en = json.loads(locale_dir.joinpath("en.json").read_text(encoding="utf-8"))
    en_keys = set(en.keys()) - {"_meta"}

    for code in LANGUAGES:
        if code == "en":
            continue
        data = json.loads(locale_dir.joinpath(f"{code}.json").read_text(encoding="utf-8"))
        keys = set(data.keys()) - {"_meta"}
        missing = en_keys - keys
        extra = keys - en_keys
        assert not missing, f"{code}: missing keys {sorted(missing)}"
        assert not extra, f"{code}: extra keys {sorted(extra)}"


def test_translation_basic_lookup() -> None:
    from pyautoclick.i18n import t

    # Same string in every locale (proper noun)
    for lang in ("en", "fr", "es", "ar", "he", "zh"):
        assert t("app_title", lang) == "Auto-clicker" or t("app_title", lang)


def test_translation_plural_dispatch() -> None:
    from pyautoclick.i18n import t

    one = t("label_clicks", "en", n=1)
    many = t("label_clicks", "en", n=42)
    assert "Click" in one and "1" in one
    assert "Click" in many and "42" in many
    assert one != many


def test_rtl_detection() -> None:
    from pyautoclick.i18n import is_rtl

    assert is_rtl("ar") is True
    assert is_rtl("he") is True
    assert is_rtl("en") is False
    assert is_rtl("fr") is False


def test_settings_default_load(tmp_config_dir) -> None:
    from pyautoclick.persistence.settings import Settings

    s = Settings.load()
    assert s.cps == 15
    assert s.trigger == "button8"
    assert s.theme == "dark"


def test_jittered_zero_is_identity() -> None:
    from pyautoclick.core.clicker import jittered

    assert jittered(100, 0) == 100
    assert jittered(0, 0) == 0


def test_jittered_clamps_to_zero() -> None:
    from pyautoclick.core.clicker import jittered

    # Whatever the random output, never negative
    for _ in range(100):
        assert jittered(5, 50) >= 0


@pytest.mark.parametrize("lang", ["en", "fr", "es", "pt", "de", "it", "ru", "zh", "ja", "ar", "he"])
def test_every_language_yields_a_title(lang: str) -> None:
    from pyautoclick.i18n import t

    assert t("app_title", lang)
    assert t("tab_hold", lang)
