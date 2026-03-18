"""
Data models for Stake Crash Predictor.
"""

from dataclasses import dataclass


@dataclass
class CrashRound:
    """Représente un round de crash avec ses données."""
    game_id: str
    timestamp: str
    multiplier: float
