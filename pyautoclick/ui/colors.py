"""Color palette used by the UI.

Centralized so a future theming system can override these in one place.
Hex values are the sv-ttk dark/light defaults plus a few app-specific accents.
"""

from __future__ import annotations

# ---- Theme fallback colors (used when ttk.Style.lookup returns "") ----
DARK_BG = "#1c1c1c"
DARK_FG = "#fafafa"
LIGHT_BG = "#fafafa"
LIGHT_FG = "#1a1a1a"

# ---- Accent ----
ACCENT_BLUE = "#3b82f6"  # default selection / focus highlight
SELECTION_FG = "#ffffff"

# ---- Tooltip (theme-agnostic, dark for contrast on most backgrounds) ----
TOOLTIP_BG = "#2b2b2b"
TOOLTIP_FG = "#eaeaea"

# ---- Status / messaging ----
ERROR_RED = "#cc4444"
WARNING_AMBER = "#d97706"  # platform caveats / non-blocking warnings
MUTED_GRAY = "gray"
