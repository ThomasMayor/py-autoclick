"""Pure-logic timing helpers used by the click engine.

This module deliberately has **no third-party dependencies** so it can be
imported and tested in any environment, including headless CI runners that
cannot load ``pynput``'s native input backends.
"""

from __future__ import annotations

import random


def jittered(value_ms: float, jitter_ms: float) -> float:
    """Return ``value_ms`` plus a uniformly-distributed jitter in ``[-jitter_ms, +jitter_ms]``.

    Always clamped to a non-negative value (a negative sleep would raise).
    When ``jitter_ms <= 0`` the function is the identity (modulo the floor).
    """
    if jitter_ms <= 0:
        return max(0.0, value_ms)
    return max(0.0, value_ms + random.uniform(-jitter_ms, jitter_ms))
