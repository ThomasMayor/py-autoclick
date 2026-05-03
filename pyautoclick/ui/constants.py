"""UI geometry, sizing and timing constants.

All magic numbers used by the UI layer live here so they can be tuned in one
place. Importing from this module is preferred over inlining numeric values.
"""

from __future__ import annotations

# ---- Window ----
WINDOW_GEOMETRY = "660x460"
WINDOW_MIN_SIZE = (620, 400)

# ---- Generic spacing ----
TAB_PADDING = 20            # ttk.Frame padding inside each tab
ROW_PADY = 8                # vertical spacing between form rows
SECTION_PADY = 12           # extra vertical space before a new section
SEPARATOR_PADY = 16
NOTEBOOK_PADX = 14
NOTEBOOK_PADY_TOP = 14
STATUS_BAR_PADDING = (14, 8)

# ---- Tooltip ----
TOOLTIP_DELAY_MS = 400
TOOLTIP_OFFSET = (20, 4)
TOOLTIP_PADX = 6
TOOLTIP_PADY = 3

# ---- Status bar ----
STATUS_BAR_LABEL_GAP = 20
STATUS_BAR_HOTKEY_GAP = 12
THEME_BUTTON_WIDTH = 3

# ---- Capture-hotkey dialog ----
CAPTURE_DIALOG_GEOMETRY = "340x130"
CAPTURE_DIALOG_PADDING = (10, 10)

# ---- CPS slider ----
CPS_SLIDER_MIN = 1
CPS_SLIDER_MAX = 50
CPS_SPINBOX_MIN = 1
CPS_SPINBOX_MAX = 200
CPS_SPINBOX_WIDTH = 5

# ---- Auto mode bounds (UI input limits) ----
AUTO_INTERVAL_MIN_MS = 1
AUTO_INTERVAL_MAX_MS = 10_000
AUTO_INTERVAL_STEP_MS = 10
AUTO_PRESS_MIN_MS = 0
AUTO_PRESS_MAX_MS = 2_000
AUTO_PRESS_STEP_MS = 5
AUTO_JITTER_MIN_MS = 0
AUTO_JITTER_MAX_MS = 2_000
AUTO_JITTER_STEP_MS = 5
AUTO_LIMIT_MIN = 0
AUTO_LIMIT_MAX = 1_000_000
AUTO_LIMIT_STEP = 10
HOLD_JITTER_MIN_MS = 0
HOLD_JITTER_MAX_MS = 500
HOLD_JITTER_STEP_MS = 5

# ---- Positions tab ----
POSITIONS_LISTBOX_HEIGHT = 4
POSITION_CAPTURE_DELAY_MS = 3000

# ---- Rendering / refresh ----
TICK_INTERVAL_MS = 100              # status bar + cursor refresh cadence
TOPMOST_FLASH_MS = 150              # bring-to-front "topmost" pulse duration

# ---- Misc ----
THEME_DARK_GLYPH = "☀"              # shown in dark mode -> button toggles to light
THEME_LIGHT_GLYPH = "☾"             # shown in light mode -> button toggles to dark
HOTKEY_CLEAR_GLYPH = "✕"
