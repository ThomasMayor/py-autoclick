"""Mouse button identifiers.

Stable language-agnostic keys -> pynput Button objects. Combobox labels are
resolved via the i18n layer (translation keys ``trigger_<key>`` and
``action_<key>``).

pynput is imported lazily
-------------------------
``pynput.mouse``'s xorg backend tries to acquire an X display at import time,
which breaks headless environments (CI runners, container builds, IDEs without
a screen). By exposing the button maps as ``_ButtonMap`` proxies, modules that
only need to *check* whether a key is valid (``persistence/migrations.py``,
``persistence/settings.py``) can import this module without triggering the
pynput chain.

The lazy load happens on the first ``__getitem__`` call, which is only made
from the UI / engine code paths that already require a display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pynput.mouse import Button

TRIGGER_KEYS = ["button8", "button9", "middle", "right"]
ACTION_KEYS = ["left", "right", "middle"]


class _ButtonMap:
    """Mapping ``str -> pynput.mouse.Button`` with deferred pynput import."""

    def __init__(self, keys: list[str]) -> None:
        self._keys: tuple[str, ...] = tuple(keys)
        self._cache: dict[str, Button] | None = None

    def _load(self) -> dict[str, Button]:
        if self._cache is None:
            from pynput.mouse import Button as _Button

            self._cache = {k: getattr(_Button, k) for k in self._keys}
        return self._cache

    def __getitem__(self, key: str) -> Button:
        return self._load()[key]

    def __contains__(self, key: object) -> bool:
        return key in self._keys

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def keys(self) -> tuple[str, ...]:
        return self._keys


TRIGGER_BUTTONS: _ButtonMap = _ButtonMap(TRIGGER_KEYS)
ACTION_BUTTONS: _ButtonMap = _ButtonMap(ACTION_KEYS)
