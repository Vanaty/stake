#!/usr/bin/env python3
"""
CLI entry point for Stake Crash Predictor.

This is the main script to run the application with various strategies and configurations.
"""

import asyncio
import argparse
from stakepred import (
    StakeCrashPredictor,
    BettingConfig,
    BetAfterBelowThresholdStrategy,
    LowStreakStrategy,
    HighAfterLowStrategy,
)


async def main():
    """Point d'entrée principal."""
    
    parser = argparse.ArgumentParser(
        description="Stake Crash Predictor avec stratégies multiples"
    )
    parser.add_argument(
        '--strategy',
        choices=['after-below', 'low-streak', 'high-after-low'],
        default='after-below',
        help='Stratégie de pari à utiliser (défaut: after-below)'
    )
    parser.add_argument(
        '--initial-balance',
        type=float,
        default=10.0,
        help='Solde initial en USDC (défaut: 10.0)'
    )
    parser.add_argument(
        '--base-bet',
        type=float,
        default=1.0,
        help='Mise de base en USDC (défaut: 1.0)'
    )
    parser.add_argument(
        '--target-multiplier',
        type=float,
        default=2.0,
        help='Multiplicateur cible (défaut: 2.0)'
    )
    parser.add_argument(
        '--martingale-multiplier',
        type=float,
        default=1.0,
        help='Multiplicateur martingale (défaut: 1.0, désactivé)'
    )
    parser.add_argument(
        '--max-martingale-steps',
        type=int,
        default=3,
        help='Nombre max de pas martingale (défaut: 3)'
    )
    parser.add_argument(
        '--entry-threshold',
        type=float,
        default=1.01,
        help='Seuil d\'entrée pour BetAfterBelowThreshold (défaut: 1.01)'
    )
    parser.add_argument(
        '--trigger-threshold',
        type=float,
        default=2.0,
        help='Seuil de déclenchement pour LowStreak (défaut: 2.0)'
    )
    parser.add_argument(
        '--trigger-streak',
        type=int,
        default=3,
        help='Nombre de rounds pour LowStreak (défaut: 3)'
    )
    parser.add_argument(
        '--pyvirtual',
        action='store_true',
        help='Activer le mode debug avec pyvirtualdisplay'
    )
    parser.add_argument(
        '--vnc',
        action='store_true',
        help='Démarrer un serveur VNC local (Linux/Ubuntu, nécessite x11vnc)'
    )
    parser.add_argument(
        '--vnc-port',
        type=int,
        default=5900,
        help='Port VNC local (défaut: 5900)'
    )
    parser.add_argument(
        '--vnc-password',
        type=str,
        default=None,
        help='Mot de passe VNC (si absent: -nopw)'
    )
    
    args = parser.parse_args()
    
    # Crée la configuration de pari
    betting_config = BettingConfig(
        initial_balance=args.initial_balance,
        target_multiplier=args.target_multiplier,
        base_bet=args.base_bet,
        martingale_multiplier=args.martingale_multiplier,
        max_martingale_steps=args.max_martingale_steps,
    )
    
    # Sélectionne la stratégie
    if args.strategy == 'after-below':
        strategy = BetAfterBelowThresholdStrategy(threshold=args.entry_threshold)
    elif args.strategy == 'low-streak':
        strategy = LowStreakStrategy(
            trigger_threshold=args.trigger_threshold,
            trigger_streak=args.trigger_streak
        )
    else:  # high-after-low
        strategy = HighAfterLowStrategy()
    
    # Lance l'application
    predictor = StakeCrashPredictor(
        strategy=strategy,
        config=betting_config,
        enable_pyvirtual=args.pyvirtual,
        enable_vnc=args.vnc,
        vnc_port=args.vnc_port,
        vnc_password=args.vnc_password,
    )
    
    await predictor.run()


if __name__ == "__main__":
    asyncio.run(main())
