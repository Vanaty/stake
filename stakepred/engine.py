"""
Game prediction engine for Stake Crash Predictor.
"""

from .strategies import Strategy
from .logger import get_logger

logger = get_logger("GamePredictionEngine")


class GamePredictionEngine:
    """Moteur de prédiction basé sur la stratégie sélectionnée."""

    def __init__(self, strategy: Strategy):
        self.strategy = strategy

    def should_bet(self, recent_history: list) -> bool:
        """Détermine s'il faut parier selon la stratégie."""
        return self.strategy.should_bet(recent_history)

    def get_strategy_name(self) -> str:
        """Retourne le nom de la stratégie."""
        return self.strategy.get_name()
