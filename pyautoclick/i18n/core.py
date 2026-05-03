"""Translation system: JSON locale files + ICU-style pluralization.

Locale files live in ``pyautoclick/i18n/locales/<code>.json``. Each is a flat
mapping ``key -> template``. Templates support :pep:`3101` ``{name}`` placeholders
and a minimal ICU subset for plurals::

    "label_clicks": "{n, plural, one {Click: {n_fmt}} other {Clicks: {n_fmt}}}"

Numbers passed as ``n=...`` are formatted via the system locale (with thousands
separators) and re-injected as ``{n_fmt}`` if referenced in the template.

Lookup cascade: requested language -> ``en`` -> raw key (with a single warning
log per missing key).
"""

from __future__ import annotations

import json
import locale as _locale_mod
import logging
import os
import re
from importlib import resources
from typing import Any

_PLURAL_HEADER_RE = re.compile(r"^(\w+)\s*,\s*plural\s*,\s*")
_FORM_RE = re.compile(r"\b(one|other)\s*\{")

logger = logging.getLogger(__name__)

LANGUAGES = ["en", "fr", "es", "pt", "de", "it", "ru", "zh", "ja", "ar"]
LANG_LABELS = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "pt": "Português",
    "de": "Deutsch",
    "it": "Italiano",
    "ru": "Русский",
    "zh": "中文",
    "ja": "日本語",
    "ar": "العربية",
}
_FALLBACK_LANG = "en"

# Loaded lazily on first use.
_TABLES: dict[str, dict[str, str]] | None = None
_MISSING_KEYS_LOGGED: set[tuple[str, str]] = set()

def _find_matching_brace(s: str, start: int) -> int:
    """Index of ``}`` matching the ``{`` at ``s[start]``. ``-1`` if unmatched."""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _parse_plural_block(inner: str, kwargs: dict[str, Any]) -> str | None:
    """Parse content of a single ``{...}`` block as ICU plural; return None if not."""
    m = _PLURAL_HEADER_RE.match(inner)
    if not m:
        return None
    var = m.group(1)
    if var not in kwargs:
        return None
    try:
        count = int(kwargs[var])
    except (TypeError, ValueError):
        return None

    forms: dict[str, str] = {}
    pos = m.end()
    while pos < len(inner):
        fm = _FORM_RE.search(inner, pos)
        if not fm:
            break
        name = fm.group(1)
        brace_open = fm.end() - 1
        brace_close = _find_matching_brace(inner, brace_open)
        if brace_close == -1:
            return None
        forms[name] = inner[brace_open + 1:brace_close]
        pos = brace_close + 1

    if "one" not in forms or "other" not in forms:
        return None
    return forms["one"] if count == 1 else forms["other"]


def _load_tables() -> dict[str, dict[str, str]]:
    """Load every JSON locale once and cache."""
    global _TABLES
    if _TABLES is not None:
        return _TABLES
    tables: dict[str, dict[str, str]] = {}
    pkg = "pyautoclick.i18n.locales"
    for code in LANGUAGES:
        try:
            text = resources.files(pkg).joinpath(f"{code}.json").read_text(encoding="utf-8")
            data = json.loads(text)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            logger.exception("failed to load locale %r", code)
            tables[code] = {}
            continue
        # Drop the optional _meta block — not a translation.
        data.pop("_meta", None)
        tables[code] = data
    _TABLES = tables
    return tables


def detect_system_language() -> str:
    """Detect the system language. Falls back to ``"en"``."""
    loc = ""
    try:
        loc = _locale_mod.getdefaultlocale()[0] or ""
    except (ValueError, OSError):
        pass
    if not loc:
        loc = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
    code = loc.split("_")[0].lower() if loc else ""
    return code if code in LANGUAGES else _FALLBACK_LANG


def _format_number(n: int) -> str:
    """Format an integer using the active locale (thousands separator)."""
    try:
        return _locale_mod.format_string("%d", n, grouping=True)
    except (TypeError, ValueError, _locale_mod.Error):
        return str(n)


def _resolve_plural(template: str, kwargs: dict[str, Any]) -> str:
    """Replace ``{var, plural, one {…} other {…}}`` blocks supporting nested braces."""
    out: list[str] = []
    i = 0
    n = len(template)
    while i < n:
        ch = template[i]
        if ch != "{":
            out.append(ch)
            i += 1
            continue
        end = _find_matching_brace(template, i)
        if end == -1:
            out.append(ch)
            i += 1
            continue
        inner = template[i + 1:end]
        replaced = _parse_plural_block(inner, kwargs)
        if replaced is not None:
            out.append(replaced)
        else:
            # Not a plural block — keep the original {...} for str.format
            out.append(template[i:end + 1])
        i = end + 1
    return "".join(out)


def _lookup(key: str, lang: str) -> str:
    tables = _load_tables()
    txt = tables.get(lang, {}).get(key)
    if txt is not None:
        return txt
    txt = tables.get(_FALLBACK_LANG, {}).get(key)
    if txt is not None:
        # Log once per (lang, key) to avoid spam at every UI tick
        marker = (lang, key)
        if marker not in _MISSING_KEYS_LOGGED:
            _MISSING_KEYS_LOGGED.add(marker)
            logger.warning("missing translation %r for lang %r — using EN fallback",
                           key, lang)
        return txt
    # Last resort: raw key, log once
    marker = ("__missing__", key)
    if marker not in _MISSING_KEYS_LOGGED:
        _MISSING_KEYS_LOGGED.add(marker)
        logger.error("translation key %r missing in ALL locales", key)
    return key


def t(key: str, lang: str, **kwargs: Any) -> str:
    """Translate ``key`` to ``lang`` with cascade EN -> raw key.

    Numeric kwargs are auto-formatted with locale thousands separator and
    exposed as ``{<name>_fmt}`` placeholders. Plural blocks dispatch on the
    raw integer value.
    """
    template = _lookup(key, lang)

    # Auto-add formatted variants for any numeric kwarg.
    expanded = dict(kwargs)
    for k, v in kwargs.items():
        if isinstance(v, int) and not isinstance(v, bool):
            expanded.setdefault(f"{k}_fmt", _format_number(v))

    # Resolve plural blocks first (they may contain other placeholders)
    template = _resolve_plural(template, expanded)

    if expanded:
        try:
            return template.format(**expanded)
        except (KeyError, IndexError):
            return template
    return template


def reset_cache() -> None:
    """For tests: drop loaded tables and missing-key markers."""
    global _TABLES
    _TABLES = None
    _MISSING_KEYS_LOGGED.clear()
