"""
Configuration for Stake Crash Predictor betting system.
"""

from dataclasses import dataclass


@dataclass
class BettingConfig:
    """Configuration centralisée pour les paramètres de pari."""
    initial_balance: float = 9.27
    target_multiplier: float = 1.09
    base_bet: float = 1.0
    martingale_multiplier: float = 11.65
    max_martingale_steps: int = 3

@dataclass
class PredictorConfig:
    """Configuration pour le moteur de prédiction."""
    prediction_threshold: float = 0.5  # Seuil de confiance pour parier