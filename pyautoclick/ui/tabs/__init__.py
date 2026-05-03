"""Tab registry. Order here = order in the notebook."""

from pyautoclick.ui.tabs.auto import AutoTab
from pyautoclick.ui.tabs.hold import HoldTab
from pyautoclick.ui.tabs.hotkeys import HotkeysTab
from pyautoclick.ui.tabs.positions import PositionsTab
from pyautoclick.ui.tabs.test import TestTab

ALL_TABS = [HoldTab, AutoTab, PositionsTab, HotkeysTab, TestTab]

__all__ = ["ALL_TABS", "AutoTab", "HoldTab", "HotkeysTab", "PositionsTab", "TestTab"]
