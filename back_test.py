
import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


@dataclass
class CrashRound:
    game_id: str
    timestamp: str
    multiplier: float


@dataclass
class BacktestResult:
    rounds_total: int
    bets_total: int
    wins: int
    losses: int
    hit_rate: float
    roi_percent: float
    final_bankroll: float
    net_profit: float
    max_drawdown: float
    avg_win: float
    avg_loss: float


class CrashHistoryLoader:
    @staticmethod
    def load(path: Path) -> list[CrashRound]:
        rounds: list[CrashRound] = []
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) < 3:
                    continue
                try:
                    rounds.append(
                        CrashRound(
                            game_id=row[0].strip(),
                            timestamp=row[1].strip(),
                            multiplier=float(row[2]),
                        )
                    )
                except ValueError:
                    continue
        return rounds


class Strategy:
    def should_bet(self, history: list[CrashRound]) -> bool:
        raise NotImplementedError


class BetAfterBelowThresholdStrategy(Strategy):
    """
    Parie au round suivant quand le crash précédent est < threshold.

    Exemple:
      threshold=1.01
      => si le dernier round a crash à 1.00, on parie le round actuel.
    """

    def __init__(self, threshold: float = 1.01) -> None:
        self.threshold = threshold

    def should_bet(self, history: list[CrashRound]) -> bool:
        if not history:
            return False
        return history[-1].multiplier < self.threshold


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

    def should_bet(self, history: list[CrashRound]) -> bool:
        if len(history) < self.trigger_streak:
            return False
        recent = history[-self.trigger_streak :]
        return all(r.multiplier <= self.trigger_threshold for r in recent)


class BackTester:
    def __init__(
        self,
        rounds: list[CrashRound],
        strategy: Strategy,
        start_bankroll: float,
        base_bet: float,
        cashout_target: float,
        martingale_multiplier: float,
        max_martingale_steps: int,
    ) -> None:
        self.rounds = rounds
        self.strategy = strategy
        self.start_bankroll = start_bankroll
        self.base_bet = base_bet
        self.cashout_target = cashout_target
        self.martingale_multiplier = martingale_multiplier
        self.max_martingale_steps = max_martingale_steps

    def run(self) -> BacktestResult:
        bankroll = self.start_bankroll
        peak_bankroll = bankroll
        max_drawdown = 0.0

        bets_total = 0
        wins = 0
        losses = 0
        profit_curve = []
        profits = []

        martingale_step = 0
        history: list[CrashRound] = [] 

        for current_round in self.rounds:
            should_bet = self.strategy.should_bet(history)

            if should_bet and bankroll > 0:
                stake = self.base_bet * (self.martingale_multiplier ** martingale_step)
                stake = min(stake, bankroll)
                if stake > 0:
                    bets_total += 1
                    if current_round.multiplier >= self.cashout_target:
                        profit = stake * (self.cashout_target - 1.0)
                        bankroll += profit
                        wins += 1
                        martingale_step = 0
                    else:
                        profit = -stake
                        bankroll += profit
                        losses += 1
                        martingale_step += 1
                        if martingale_step > self.max_martingale_steps:
                            martingale_step = 0

                    profits.append(profit)
                    profit_curve.append(bankroll)
                    peak_bankroll = max(peak_bankroll, bankroll)
                    drawdown = peak_bankroll - bankroll
                    max_drawdown = max(max_drawdown, drawdown)

            history.append(current_round)
            if len(history) > 20:
                history.pop(0)

        hit_rate = (wins / bets_total * 100) if bets_total else 0.0
        net_profit = bankroll - self.start_bankroll
        roi_percent = (net_profit / self.start_bankroll * 100) if self.start_bankroll else 0.0

        win_profits = [p for p in profits if p > 0]
        loss_profits = [p for p in profits if p < 0]

        return BacktestResult(
            rounds_total=len(self.rounds),
            bets_total=bets_total,
            wins=wins,
            losses=losses,
            hit_rate=hit_rate,
            roi_percent=roi_percent,
            final_bankroll=bankroll,
            net_profit=net_profit,
            max_drawdown=max_drawdown,
            avg_win=mean(win_profits) if win_profits else 0.0,
            avg_loss=mean(loss_profits) if loss_profits else 0.0,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backtest de stratégie sur crash_history.csv"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("crash_history.csv"),
        help="Chemin du fichier CSV (défaut: crash_history.csv)",
    )
    parser.add_argument(
        "--bankroll",
        type=float,
        default=100.0,
        help="Bankroll initiale",
    )
    parser.add_argument(
        "--bet",
        type=float,
        default=1.0,
        help="Mise de base",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=2.0,
        help="Cashout cible (ex: 2.0)",
    )
    parser.add_argument(
        "--strategy",
        choices=["after-below", "low-streak"],
        default="after-below",
        help="Type de stratégie (défaut: after-below)",
    )
    parser.add_argument(
        "--entry-threshold",
        type=float,
        default=1.01,
        help="Pour after-below: parie si le crash précédent est < ce seuil",
    )
    parser.add_argument(
        "--trigger-threshold",
        type=float,
        default=2.0,
        help="Seuil de multiplicateur faible pour déclencher",
    )
    parser.add_argument(
        "--trigger-streak",
        type=int,
        default=3,
        help="Nombre de rounds faibles consécutifs pour déclencher",
    )
    parser.add_argument(
        "--martingale",
        type=float,
        default=1.0,
        help="Multiplicateur martingale (1.0 = désactivé)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Nombre max de paliers martingale avant reset",
    )
    return parser


def print_result(result: BacktestResult) -> None:
    print("\n===== Résultat Backtest =====")
    print(f"Rounds total        : {result.rounds_total}")
    print(f"Bets total          : {result.bets_total}")
    print(f"Wins / Losses       : {result.wins} / {result.losses}")
    print(f"Hit rate            : {result.hit_rate:.2f}%")
    print(f"ROI                 : {result.roi_percent:.2f}%")
    print(f"Bankroll finale     : {result.final_bankroll:.4f}")
    print(f"Profit net          : {result.net_profit:.4f}")
    print(f"Max drawdown        : {result.max_drawdown:.4f}")
    print(f"Gain moyen (win)    : {result.avg_win:.4f}")
    print(f"Perte moyenne (loss): {result.avg_loss:.4f}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.bankroll <= 0:
        raise ValueError("--bankroll doit être > 0")
    if args.bet <= 0:
        raise ValueError("--bet doit être > 0")
    if args.target <= 1.0:
        raise ValueError("--target doit être > 1.0")
    if args.entry_threshold <= 1.0:
        raise ValueError("--entry-threshold doit être > 1.0")
    if args.trigger_streak <= 0:
        raise ValueError("--trigger-streak doit être > 0")
    if args.martingale < 1.0:
        raise ValueError("--martingale doit être >= 1.0")
    if args.max_steps < 0:
        raise ValueError("--max-steps doit être >= 0")

    rounds = CrashHistoryLoader.load(args.csv)
    if not rounds:
        raise RuntimeError(f"Aucune donnée exploitable dans {args.csv}")

    if args.strategy == "after-below":
        strategy = BetAfterBelowThresholdStrategy(threshold=args.entry_threshold)
    else:
        strategy = LowStreakStrategy(
            trigger_threshold=args.trigger_threshold,
            trigger_streak=args.trigger_streak,
        )

    result = BackTester(
        rounds=rounds,
        strategy=strategy,
        start_bankroll=args.bankroll,
        base_bet=args.bet,
        cashout_target=args.target,
        martingale_multiplier=args.martingale,
        max_martingale_steps=args.max_steps,
    ).run()

    print_result(result)


if __name__ == "__main__":
    main()