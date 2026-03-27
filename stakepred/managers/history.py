"""
Game history manager for Stake Crash Predictor.
Handles persistence and management of crash rounds.
"""

import os
from typing import TYPE_CHECKING

from ..logger import get_logger

if TYPE_CHECKING:
    from ..models import CrashRound

logger = get_logger("GameHistoryManager")


class GameHistoryManager:
    """Gère l'historique des jeux et la sauvegarde des données."""

    def __init__(self, history_file: str = 'crash_history.csv'):
        self.history_file = history_file
        self.rounds: list["CrashRound"] = []
        self._initialize_file()

    def _initialize_file(self):
        """Initialise le fichier d'historique s'il n'existe pas."""
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                f.write("game_id,timestamp,multiplier,target\n")  # Crée un fichier vide

    async def save_round(self, game_id: str, timestamp: str, crashpoint: float, target: float = 2) -> None:
        """Sauvegarde un round dans l'historique."""
        from datetime import datetime, timezone
        
        try:
            parsed_time = datetime.strptime(timestamp, "%a, %d %b %Y %H:%M:%S %Z")
            start_time = parsed_time.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            start_time = timestamp
        
        with open(self.history_file, 'a') as f:
            f.write(f"{game_id},{start_time},{crashpoint},{target}\n")
        
        from ..models import CrashRound
        round_obj = CrashRound(game_id=game_id, timestamp=timestamp, multiplier=crashpoint)
        self.rounds.append(round_obj)
        if self.rounds and len(self.rounds) > 50:
            self.rounds.pop(0)  # Limite la mémoire 
        logger.debug(f"Round sauvegardé: {game_id} -> {crashpoint}x")

    def get_recent_rounds(self, limit: int = 10) -> list["CrashRound"]:
        """Retourne les derniers rounds (jusqu'à limit)."""
        return self.rounds[-limit:] if self.rounds else []
