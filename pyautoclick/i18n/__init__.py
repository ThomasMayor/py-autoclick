"""i18n public API."""

from pyautoclick.i18n.core import (
    LANG_LABELS,
    LANGUAGES,
    detect_system_language,
    t,
)
from pyautoclick.i18n.direction import get_direction, is_rtl

__all__ = [
    "t",
    "detect_system_language",
    "LANGUAGES",
    "LANG_LABELS",
    "is_rtl",
    "get_direction",
]
