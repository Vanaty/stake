"""
Betting manager for Stake Crash Predictor.
Handles bankroll, martingale logic, and betting statistics.
"""

from typing import Optional
from ..config import BettingConfig
from ..logger import get_logger

logger = get_logger("BettingManager")


class BettingManager:
    """Gère la logique de pari et le suivi du bankroll."""

    def __init__(self, config: BettingConfig):
        self.config = config
        self.balance = config.initial_balance
        self.profit = 0.0
        self.martingale_step = 0
        self.is_betting = False
        self.current_bet_amount = 0.0
        self.total_bets = 0
        self.wins = 0
        self.losses = 0

    def calculate_next_bet(self) -> float:
        """Calcule le montant du prochain pari basé sur la séquence martingale."""
        return self.config.base_bet * (self.config.martingale_multiplier ** self.martingale_step)

    def can_place_bet(self) -> bool:
        """Vérifie si un pari peut être placé (assez de balance)."""
        next_bet = self.calculate_next_bet()
        return next_bet <= self.balance and self.martingale_step < self.config.max_martingale_steps

    def place_bet(self, amount: float) -> bool:
        """Place un pari et met à jour l'état."""
        if amount > self.balance:
            logger.warning(f"Insuffisant de balance. Demandé: {amount}, Disponible: {self.balance}")
            return False
        
        self.current_bet_amount = amount
        self.is_betting = True
        self.total_bets += 1
        return True

    def resolve_win(self) -> None:
        """Résout une victoire."""
        profit = (self.config.target_multiplier - 1) * self.current_bet_amount
        self.balance += profit
        self.profit += profit
        self.martingale_step = 0
        self.wins += 1
        self.is_betting = False
        logger.success(f"Pari gagné! +{profit:.2f} USDC. Profit total: {self.profit:.2f} USDC")

    def resolve_loss(self) -> None:
        """Résout une perte."""
        self.balance -= self.current_bet_amount
        self.profit -= self.current_bet_amount
        self.martingale_step += 1
        self.losses += 1
        self.is_betting = False
        logger.error(f"Pari perdu! -{self.current_bet_amount:.2f} USDC. Profit total: {self.profit:.2f} USDC")

    def reset_martingale(self) -> None:
        """Réinitialise le compteur martingale."""
        self.martingale_step = 0

    def get_stats(self) -> dict:
        """Retourne les statistiques actuelles."""
        hit_rate = (self.wins / self.total_bets * 100) if self.total_bets > 0 else 0.0
        return {
            'balance': self.balance,
            'profit': self.profit,
            'total_bets': self.total_bets,
            'wins': self.wins,
            'losses': self.losses,
            'hit_rate': hit_rate,
            'martingale_step': self.martingale_step,
            'current_bet': self.current_bet_amount,
        }
