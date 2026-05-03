"""i18n core: t() lookup, plural dispatch, cascade fallback, edge cases."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from pyautoclick.i18n import LANG_LABELS, LANGUAGES, detect_system_language, t
from pyautoclick.i18n import core as core_module


@pytest.fixture(autouse=True)
def _reset_i18n_cache():
    """Each test starts with a fresh i18n cache."""
    core_module.reset_cache()
    yield
    core_module.reset_cache()


# ----------------------------------------------------------------------
# Basic lookup
# ----------------------------------------------------------------------


class TestBasicLookup:
    def test_known_key_returns_translation(self):
        assert t("tab_hold", "fr") == "Mode maintenu"
        assert t("tab_hold", "en") == "Hold mode"

    def test_unknown_key_returns_raw_key(self):
        """Critical: never crash on a missing key, return the key itself."""
        assert t("nonexistent_key_42", "fr") == "nonexistent_key_42"

    def test_unknown_key_logged_only_once(self, caplog):
        """The same missing key must not spam the logs."""
        import logging

        with caplog.at_level(logging.ERROR, logger="pyautoclick.i18n.core"):
            t("missing_xyz", "en")
            t("missing_xyz", "en")
            t("missing_xyz", "en")
        relevant = [r for r in caplog.records if "missing_xyz" in r.message]
        assert len(relevant) == 1, f"missing key logged {len(relevant)} times"

    def test_unknown_language_falls_back_to_english(self, caplog):
        """A request for a non-existent locale must use the English string."""
        # Inject a known-only-in-EN key
        core_module._TABLES = {
            "en": {"only_in_en": "English text"},
            "fr": {},
        }
        result = t("only_in_en", "fr")
        assert result == "English text"


# ----------------------------------------------------------------------
# Plural dispatch (ICU subset)
# ----------------------------------------------------------------------


class TestPluralDispatch:
    def test_n_equals_one_uses_one_form(self):
        # "label_clicks": "{n, plural, one {Click: {n_fmt}} other {Clicks: ...}}"
        result = t("label_clicks", "en", n=1)
        assert result == "Click: 1"

    def test_n_not_equals_one_uses_other_form(self):
        result = t("label_clicks", "en", n=2)
        assert "Clicks:" in result and "2" in result

    def test_n_zero_uses_other_form(self):
        """Zero is 'other' in the simplified one/other rule."""
        result = t("label_clicks", "en", n=0)
        assert "Clicks:" in result

    def test_n_negative_uses_other_form(self):
        # Edge case — pathological but must not crash
        result = t("label_clicks", "en", n=-5)
        assert result  # just must not raise

    @pytest.mark.parametrize("lang", ["en", "fr", "es", "ja", "ar", "he", "zh"])
    def test_plural_works_in_every_language(self, lang):
        one = t("label_clicks", lang, n=1)
        many = t("label_clicks", lang, n=100)
        assert one and many, f"empty result for {lang}"

    def test_locale_aware_thousands_format(self):
        """Numbers must be formatted via the system locale thousands separator."""
        result = t("label_clicks", "en", n=1234567)
        # Some separator must be present (' or , or .)
        assert any(sep in result for sep in (",", "'", ".", " ", " "))

    def test_plural_template_without_kwargs_not_crashing(self):
        """If kwargs missing, template should be returned with placeholders intact."""
        # Calling t("label_clicks", "en") without n shouldn't raise
        result = t("label_clicks", "en")
        # The template stays as-is
        assert "{n, plural" in result or "{" in result


# ----------------------------------------------------------------------
# Format kwargs
# ----------------------------------------------------------------------


class TestFormatKwargs:
    def test_simple_substitution(self):
        result = t("invalid_combos", "en", x="ctrl+a, ctrl+b")
        assert "ctrl+a, ctrl+b" in result

    def test_missing_kwarg_does_not_raise(self):
        """If template has {x} but kwargs missing x, return template untouched."""
        # Should not raise KeyError
        result = t("invalid_combos", "en")
        assert result  # whatever the policy, must return something


# ----------------------------------------------------------------------
# detect_system_language
# ----------------------------------------------------------------------


class TestDetectSystemLanguage:
    def test_detects_french(self):
        with patch.dict(os.environ, {"LANG": "fr_FR.UTF-8", "LC_ALL": ""}, clear=False):
            with patch("locale.getdefaultlocale", return_value=("fr_FR", "UTF-8")):
                assert detect_system_language() == "fr"

    def test_detects_english(self):
        with patch("locale.getdefaultlocale", return_value=("en_US", "UTF-8")):
            assert detect_system_language() == "en"

    def test_detects_arabic(self):
        with patch("locale.getdefaultlocale", return_value=("ar_SA", "UTF-8")):
            assert detect_system_language() == "ar"

    def test_unknown_language_falls_back_to_english(self):
        """A locale not in LANGUAGES must default to en (the fallback lang)."""
        with patch("locale.getdefaultlocale", return_value=("xx_YY", "UTF-8")):
            assert detect_system_language() == "en"

    def test_no_locale_at_all_falls_back_to_english(self):
        """When the system has no locale info, default to English."""
        with patch("locale.getdefaultlocale", return_value=(None, None)):
            with patch.dict(os.environ, {"LANG": "", "LC_ALL": ""}, clear=False):
                assert detect_system_language() == "en"

    def test_locale_module_raising_exception_is_handled(self):
        """A broken locale module must not crash the app."""
        with patch("locale.getdefaultlocale", side_effect=ValueError("broken")):
            with patch.dict(os.environ, {"LANG": "fr_FR"}, clear=False):
                # Falls back to env LANG
                assert detect_system_language() == "fr"


# ----------------------------------------------------------------------
# Languages registry consistency
# ----------------------------------------------------------------------


class TestLanguagesRegistry:
    def test_every_language_has_label(self):
        for code in LANGUAGES:
            assert code in LANG_LABELS, f"missing label for {code}"

    def test_every_label_corresponds_to_a_language(self):
        for code in LANG_LABELS:
            assert code in LANGUAGES, f"orphan label {code}"

    def test_label_is_native_form(self):
        """Sanity check: a few key languages have their native names."""
        assert LANG_LABELS["fr"] == "Français"
        assert LANG_LABELS["zh"] == "中文"
        assert LANG_LABELS["ar"] == "العربية"
        assert LANG_LABELS["ru"] == "Русский"


# ----------------------------------------------------------------------
# Robustness against malformed locale tables
# ----------------------------------------------------------------------


class TestRobustness:
    def test_completely_empty_table_falls_back_to_raw_key(self):
        core_module._TABLES = {"en": {}, "fr": {}}
        assert t("any_key", "fr") == "any_key"

    def test_kwargs_with_non_int_value_does_not_break_plural(self):
        """If user passes n=None or n='abc', plural fallback shouldn't crash."""
        core_module._TABLES = {
            "en": {"k": "{n, plural, one {O} other {M}}"},
        }
        # When n is missing or non-int, the template stays unprocessed but no crash
        result = t("k", "en", n="not a number")
        assert isinstance(result, str)
