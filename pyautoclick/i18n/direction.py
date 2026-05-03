"""Right-to-left support for RTL languages (Arabic, Hebrew, Persian…).

The direction is read from the locale's ``_meta.direction`` field. Currently
only Arabic ships an RTL declaration; adding new RTL languages just requires
``"direction": "rtl"`` in the new locale's ``_meta`` block.
"""

from __future__ import annotations

import json
import logging
from importlib import resources

logger = logging.getLogger(__name__)

# Hardcoded fallback for languages we know are RTL even before reading the
# JSON, so the layout is correct on the very first render.
_KNOWN_RTL = {"ar", "he", "fa", "ur"}

_CACHE: dict[str, str] = {}


def get_direction(lang: str) -> str:
    """Return ``"rtl"`` or ``"ltr"`` for the given language code."""
    if lang in _CACHE:
        return _CACHE[lang]
    direction = "ltr"
    try:
        text = resources.files("pyautoclick.i18n.locales").joinpath(
            f"{lang}.json"
        ).read_text(encoding="utf-8")
        meta = json.loads(text).get("_meta", {})
        if isinstance(meta, dict) and meta.get("direction") == "rtl":
            direction = "rtl"
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        # Fall back to the hardcoded set
        if lang in _KNOWN_RTL:
            direction = "rtl"
    _CACHE[lang] = direction
    return direction


def is_rtl(lang: str) -> bool:
    return get_direction(lang) == "rtl"


def reset_cache() -> None:
    """For tests."""
    _CACHE.clear()
