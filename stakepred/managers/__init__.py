"""
Package for manager classes.
"""

from .api import StakeAPIClient
from .betting import BettingManager
from .browser import BrowserManager
from .history import GameHistoryManager
from .predictor import AdvancedPredictor

__all__ = [
    "StakeAPIClient",
    "BettingManager",
    "BrowserManager",
    "GameHistoryManager",
    "AdvancedPredictor",
]
