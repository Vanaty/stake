"""
Main predictor class for Stake Crash Predictor.
"""

import asyncio
import json
from typing import Optional

from .strategies import Strategy
from .config import BettingConfig
from .managers import BrowserManager, BettingManager, GameHistoryManager, StakeAPIClient
from .engine import GamePredictionEngine
from .logger import get_logger

logger = get_logger("StakeCrashPredictor")


class StakeCrashPredictor:
    """Application principale pour la prédiction et le pari sur le crash."""

    def __init__(
        self,
        strategy: Strategy,
        config: Optional[BettingConfig] = None,
        enable_pyvirtual: bool = False,
        enable_vnc: bool = False,
        vnc_port: int = 5900,
        vnc_password: Optional[str] = None,
    ):
        self.config = config or BettingConfig()
        self.strategy = strategy
        
        # Composants
        self.browser_manager = BrowserManager(
            enable_pyvirtual=enable_pyvirtual,
            enable_vnc=enable_vnc,
            vnc_port=vnc_port,
            vnc_password=vnc_password,
        )
        self.betting_manager = BettingManager(self.config)
        self.game_history = GameHistoryManager()
        self.api_client: Optional[StakeAPIClient] = None
        self.prediction_engine = GamePredictionEngine(strategy)
        
        # États
        self.is_predicting = False
        self.is_betting = False
        self.running = False

    async def initialize(self):
        """Initialise tous les composants."""
        logger.info("Initialisation de l'application...")
        await self.browser_manager.initialize()
        self.api_client = StakeAPIClient(self.browser_manager.crash_page)
        
        def websocket_handler(ws):
            if ws.url.endswith("/_api/websockets"):
                logger.info(f"WebSocket connecté: {ws.url}")
                ws.on("framereceived", lambda frame: asyncio.create_task(self.handle_game_event(json.loads(frame))))
                return ws
        self.browser_manager.crash_page.on("websocket", websocket_handler)
        
        await self.browser_manager.navigate_to_game()
        # Récupère le solde actuel
        balance = await self.api_client.fetch_user_balance()
        if balance is not None:
            self.betting_manager.balance = balance
            logger.success(f"Solde initial: {balance:.2f} USDC")
        logger.success("Application initialisée avec succès")

    async def handle_game_event(self, event_data: dict):
        """Traite les événements de jeu reçus via WebSocket."""
        crash_event = event_data.get('payload', {}).get('data', {}).get('crash', {}).get('event', {})
        game_id = crash_event.get('id')
        status = crash_event.get('status')
        
        if status == 'starting' and not self.is_predicting:
            self.is_predicting = True
            logger.debug("Nouveau jeu en cours...")
        
        if status == 'starting' and self.is_betting:
            self.is_betting = False
            await self._place_bet()

        elif status == 'crash':
            self.is_predicting = False
            crashpoint = crash_event.get('multiplier')
            timestamp = crash_event.get('timestamp')
            
            # Sauvegarde le round
            await self.game_history.save_round(game_id, timestamp, crashpoint)
            logger.info(f"Crash point réel: {crashpoint}x")
            
            # Résout le pari précédent s'il y en a un
            if self.betting_manager.is_betting:
                if crashpoint >= self.config.target_multiplier:
                    self.betting_manager.resolve_win()
                else:
                    self.betting_manager.resolve_loss()
            
            # Vérifie si on doit parier pour le prochain round
            recent_history = self.game_history.get_recent_rounds(limit=10)
            if self.prediction_engine.should_bet(recent_history):
                self.is_betting = True

    async def _place_bet(self):
        """Place un pari selon la configuration."""
        if not self.betting_manager.can_place_bet():
            if self.betting_manager.martingale_step >= self.config.max_martingale_steps:
                logger.warning("Nombre max de pas martingale atteint, réinitialisation...")
                self.betting_manager.reset_martingale()
            else:
                logger.warning("Solde insuffisant pour placer le pari")
            return
        
        if self.api_client is None:
            logger.error("Client API non initialisé, impossible de placer le pari réel")
            return

        amount = self.betting_manager.calculate_next_bet()
        placed_on_platform, reason = await self.api_client.place_crash_bet_api(
            amount=amount,
            cashout_multiplier=self.config.target_multiplier,
        )

        if not placed_on_platform:
            logger.warning(f"Pari non envoyé sur Stake: {reason}")
            return

        if self.betting_manager.place_bet(amount):
            logger.info(f"Pari RÉEL placé: {amount:.2f} USDC à {self.config.target_multiplier}x")

    def _display_stats(self):
        """Affiche les statistiques actuelles."""
        stats = self.betting_manager.get_stats()
        logger.info("=" * 50)
        logger.info(f"Stratégie: {self.prediction_engine.get_strategy_name()}")
        logger.info(f"Solde: {stats['balance']:.2f} USDC")
        logger.info(f"Profit total: {stats['profit']:.2f} USDC")
        logger.info(f"Nombre de paris: {stats['total_bets']}")
        logger.info(f"Victoires/Pertes: {stats['wins']}/{stats['losses']}")
        logger.info(f"Taux de réussite: {stats['hit_rate']:.2f}%")
        logger.info(f"Pas martingale actuel: {stats['martingale_step']}/{self.config.max_martingale_steps}")
        logger.info("=" * 50)

    async def run(self):
        """Exécute l'application principale."""
        try:
            await self.initialize()
            self.running = True
            
            # Boucle d'interaction
            logger.info("Application en attente de commandes...")
            while self.running:
                user_input = await asyncio.to_thread(
                    input, 
                    "Commandes: 'info' (stats), 'exit' (quitter) > "
                )
                
                if user_input.lower() == 'exit':
                    self.running = False
                    logger.info("Arrêt de l'application...")
                elif user_input.lower() == 'info':
                    self._display_stats()
                else:
                    logger.warning(f"Commande inconnue: {user_input}")

        except Exception as e:
            logger.error(f"Erreur: {e}", exc_info=True)
        finally:
            await self.browser_manager.close()
            logger.info("Application terminée")
