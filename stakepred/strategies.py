"""
Betting strategies for Stake Crash Predictor.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CrashRound


class Strategy(ABC):
    """Interface abstraite pour les stratégies de pari."""

    @abstractmethod
    def should_bet(self, history: list["CrashRound"]) -> bool:
        """Détermine s'il faut parier sur le prochain round."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Retourne le nom de la stratégie."""
        pass


class BetAfterBelowThresholdStrategy(Strategy):
    """
    Parie au round suivant quand le crash précédent est < threshold.
    
    Exemple:
      threshold=1.01
      => si le dernier round a crash à 1.00, on parie le round actuel.
    """

    def __init__(self, threshold: float = 1.01, target: float = 1.09) -> None:
        self.threshold = threshold
        self.target = target

    def should_bet(self, history: list["CrashRound"]) -> bool:
        if not history:
            return False
        if len(history) >= 2:
            recent = history[-2:]
            if all(r.multiplier < self.target + 0.01 for r in recent[-2:]):
                return True
        return history[-1].multiplier < self.threshold

    def get_name(self) -> str:
        return f"BetAfterBelowThreshold(threshold={self.threshold}, target={self.target})"


class LowStreakStrategy(Strategy):
    """
    Parie après une série de multiplicateurs faibles.

    Exemple:
      trigger_threshold=2.0, trigger_streak=3
      => parie quand les 3 derniers rounds sont <= 2.0
    """

    def __init__(self, trigger_threshold: float, trigger_streak: int) -> None:
        self.trigger_threshold = trigger_threshold
        self.trigger_streak = trigger_streak

    def should_bet(self, history: list["CrashRound"]) -> bool:
        if len(history) < self.trigger_streak:
            return False
        recent = history[-self.trigger_streak :]
        return all(r.multiplier <= self.trigger_threshold for r in recent)

    def get_name(self) -> str:
        return f"LowStreak(threshold={self.trigger_threshold}, streak={self.trigger_streak})"


class HighAfterLowStrategy(Strategy):
    """
    Parie après une baisse pour anticiper un rebound.
    
    Exemple:
      drop_threshold=0.15, rebound_threshold=1.5
      => parie si crash précédent < moyenne * (1 - drop_threshold)
    """

    def __init__(self, drop_threshold: float = 0.15, rebound_threshold: float = 1.5) -> None:
        self.drop_threshold = drop_threshold
        self.rebound_threshold = rebound_threshold

    def should_bet(self, history: list["CrashRound"]) -> bool:
        if len(history) < 2:
            return False
        
        recent = history[-2:]
        avg = sum(r.multiplier for r in history[-10:]) / min(len(history), 10)
        last_multiplier = recent[-1].multiplier
        
        return last_multiplier < avg * (1 - self.drop_threshold)

    def get_name(self) -> str:
        return f"HighAfterLow(drop={self.drop_threshold}, rebound={self.rebound_threshold})"
