"""
Package for manager classes.
"""

from .api import StakeAPIClient
from .betting import BettingManager
from .browser import BrowserManager
from .history import GameHistoryManager

__all__ = [
    "StakeAPIClient",
    "BettingManager",
    "BrowserManager",
    "GameHistoryManager",
]
