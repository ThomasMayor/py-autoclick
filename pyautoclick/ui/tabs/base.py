"""Abstract base class for notebook tabs.

Includes RTL-aware layout helpers. Subclasses should use ``self.col(0)`` /
``self.col(1)`` and ``self.side("left")`` / ``self.side("right")`` instead of
hardcoded values so the layout mirrors automatically for RTL languages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from tkinter import ttk
from typing import ClassVar

from pyautoclick.i18n import is_rtl
from pyautoclick.ui.constants import TAB_PADDING
from pyautoclick.ui.context import AppContext


class BaseTab(ttk.Frame, ABC):
    """Common contract: ``title_key`` + ``build()``.

    RTL helpers
    -----------
    For a 2-column "label + control" layout, use ``self.col(0)`` for the label
    column and ``self.col(1)`` for the control column. In LTR these return 0/1
    respectively; in RTL they return 1/0, which combined with ``anchor=self.anchor_label``
    gives a proper mirrored layout.

    For ``pack(side=...)``, use ``self.side("left")`` / ``self.side("right")``.
    """

    title_key: ClassVar[str] = ""

    def __init__(self, parent: ttk.Widget, ctx: AppContext) -> None:
        super().__init__(parent, padding=TAB_PADDING)
        self.ctx = ctx
        self._rtl = is_rtl(ctx.settings.language or "en")
        # Make column 0 (the label column in LTR) be the one that *doesn't*
        # absorb extra width — controls expand. Inverted in RTL.
        self.build()

    @abstractmethod
    def build(self) -> None:
        """Construct widgets. Subclasses must implement."""

    # ------------------------------------------------------------------
    # RTL helpers (no-ops in LTR, mirroring in RTL)
    # ------------------------------------------------------------------

    @property
    def is_rtl(self) -> bool:
        return self._rtl

    def col(self, n: int) -> int:
        """Return ``n`` as-is (LTR) or its mirror (RTL)."""
        if not self._rtl:
            return n
        # 2-column layouts only: 0↔1
        return 1 - n

    def side(self, s: str) -> str:
        """Mirror ``"left"`` / ``"right"`` in RTL."""
        if not self._rtl:
            return s
        if s == "left":
            return "right"
        if s == "right":
            return "left"
        return s

    @property
    def anchor_label(self) -> str:
        """Anchor for label-style text: east in RTL, west in LTR."""
        return "e" if self._rtl else "w"

    @property
    def sticky_label(self) -> str:
        """``sticky=`` value for the label column."""
        return "e" if self._rtl else "w"

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    @property
    def settings(self):
        return self.ctx.settings

    @property
    def t(self):
        return self.ctx.t

    @property
    def clicker(self):
        return self.ctx.clicker

    def commit(self) -> None:
        self.ctx.commit()
