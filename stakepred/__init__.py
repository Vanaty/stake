"""
Stake Crash Predictor - Main package.

A professional-grade betting application with multiple strategies and modular architecture.
"""

from .strategies import (
    Strategy,
    BetAfterBelowThresholdStrategy,
    LowStreakStrategy,
    HighAfterLowStrategy,
)
from .config import BettingConfig
from .models import CrashRound
from .predictor import StakeCrashPredictor
from .engine import GamePredictionEngine
from .logger import get_logger

from .managers import (
    StakeAPIClient,
    BettingManager,
    BrowserManager,
    GameHistoryManager,
)

__version__ = "2.0.0"
__author__ = "Vanaty"

__all__ = [
    # Strategies
    "Strategy",
    "BetAfterBelowThresholdStrategy",
    "LowStreakStrategy",
    "HighAfterLowStrategy",
    
    # Configuration
    "BettingConfig",
    
    # Models
    "CrashRound",
    
    # Main Application
    "StakeCrashPredictor",
    "GamePredictionEngine",
    
    # Managers
    "StakeAPIClient",
    "BettingManager",
    "BrowserManager",
    "GameHistoryManager",
    
    # Utilities
    "get_logger",
]
