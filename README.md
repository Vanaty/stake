# Stake Crash Predictor

Application avancée de prédiction et de pari automatique pour le jeu Crash sur Stake.com avec support de multiples stratégies.

## Architecture

L'application est structurée suivant les principes SOLID et les bonnes pratiques OOP:

### Classes Principales

#### 1. **Strategy Pattern**
- `Strategy` (interface abstraite)
- `BetAfterBelowThresholdStrategy` - Parie quand le crash précédent < seuil
- `LowStreakStrategy` - Parie après une série de crashes faibles
- `HighAfterLowStrategy` - Parie en anticipant un rebound après une baisse

#### 2. **Data Models**
- `CrashRound` - Représente un round avec game_id, timestamp et multiplier
- `BettingConfig` - Configuration centralisée pour les paramètres de pari

#### 3. **Core Managers**
- `BettingManager` - Gère la logique de pari, le bankroll et les statistiques
- `StakeAPIClient` - Interface avec l'API GraphQL de Stake
- `GameHistoryManager` - Persiste et gère l'historique des jeux
- `GamePredictionEngine` - Moteur de prédiction basé sur la stratégie
- `BrowserManager` - Gère le cycle de vie du navigateur Playwright

#### 4. **Application Principale**
- `StakeCrashPredictor` - Orchestre tous les composants

## Utilisation

### Installation

```bash
pip install patchright
pip install pyvirtualdisplay  # Optionnel, pour debug
```

### Exemples d'utilisation

#### 1. Stratégie "After Below" (par défaut)
```bash
python stake.py --strategy after-below --entry-threshold 1.01 --base-bet 1.0
```

#### 2. Stratégie "Low Streak"
```bash
python stake.py --strategy low-streak \
  --trigger-threshold 2.0 \
  --trigger-streak 3 \
  --base-bet 1.0
```

#### 3. Stratégie "High After Low"
```bash
python stake.py --strategy high-after-low --base-bet 1.0
```

#### 4. Configuration personnalisée
```bash
python stake.py \
  --strategy after-below \
  --initial-balance 50.0 \
  --base-bet 2.0 \
  --target-multiplier 1.15 \
  --martingale-multiplier 2.0 \
  --max-martingale-steps 5
```

### Options CLI

| Option | Type | Défaut | Description |
|--------|------|--------|-------------|
| `--strategy` | string | after-below | Stratégie: after-below, low-streak, high-after-low |
| `--initial-balance` | float | 9.27 | Solde initial en USDC |
| `--base-bet` | float | 1.0 | Mise de base en USDC |
| `--target-multiplier` | float | 1.09 | Multiplicateur cible pour cashout |
| `--martingale-multiplier` | float | 11.65 | Multiplicateur martingale |
| `--max-martingale-steps` | int | 3 | Nombre max de niveaux martingale |
| `--entry-threshold` | float | 1.01 | Seuil d'entrée (BetAfterBelow) |
| `--trigger-threshold` | float | 2.0 | Seuil de déclenchement (LowStreak) |
| `--trigger-streak` | int | 3 | Nombre de rounds faibles (LowStreak) |
| `--pyvirtual` | flag | false | Active le mode debug avec pyvirtualdisplay |

## Stratégies Expliquées

### 1. BetAfterBelowThreshold
**Principe**: Parie au round suivant si le crash précédent était en dessous d'un seuil.

```python
BetAfterBelowThresholdStrategy(threshold=1.01)
# Parie si dernier crash < 1.01x
```

**Avantage**: Simple et efficace sur les crashes faibles
**Risque**: Peut ignorer les patterns long-terme

### 2. LowStreak
**Principe**: Parie après une série de crashes faibles consécutifs (suppose un rebound).

```python
LowStreakStrategy(trigger_threshold=2.0, trigger_streak=3)
# Parie si les 3 derniers crashes <= 2.0x
```

**Avantage**: Capture les retournements après dry spells
**Risque**: Les crashes faibles peuvent continuer

### 3. HighAfterLow
**Principe**: Parie en anticipant un rebound après une baisse significative de la moyenne.

```python
HighAfterLowStrategy(drop_threshold=0.15, rebound_threshold=1.5)
# Parie si crash actuel < moyenne * 0.85
```

**Avantage**: Détecte les anomalies dans les patterns
**Risque**: Faux signaux sur patterns en mutation

## Système de Pari

### Martingale Simple
- Débute avec `base_bet`
- En cas de perte: bet suivant = bet précédent × `martingale_multiplier`
- Reset après victoire ou atteinte du `max_martingale_steps`

### Gestion du Bankroll
```python
BettingManager gère:
- Balance actuelle
- Profit/Loss cumulé
- État martingale
- Statistiques de paris
```

## Architecture Détaillée

```
StakeCrashPredictor (Main)
├── BrowserManager (Playwright lifecycle)
├── BettingManager (Bankroll & pari logic)
├── GameHistoryManager (CSV persistence)
├── StakeAPIClient (GraphQL interface)
├── GamePredictionEngine (Strategy wrapper)
└── Strategy (Abstract base)
    ├── BetAfterBelowThresholdStrategy
    ├── LowStreakStrategy
    └── HighAfterLowStrategy
```

## Bonnes Pratiques Implémentées

✅ **SOLID Principles**
- Single Responsibility: Chaque classe a une responsabilité unique
- Open/Closed: Facile d'ajouter nouvelles stratégies
- Liskov Substitution: Strategies interchangeables
- Interface Segregation: APIs minimales et focalisées
- Dependency Inversion: Injecte les dépendances

✅ **Design Patterns**
- Strategy Pattern pour les stratégies de pari
- Manager Pattern pour organiser les responsabilités
- Factory Pattern implicite dans le CLI

✅ **Code Quality**
- Type hints complets
- Docstrings pour chaque classe/méthode
- Logging structuré avec couleurs
- Gestion d'erreurs appropriée
- Séparation des concerns

✅ **Configuration**
- `BettingConfig` dataclass pour configuration centralisée
- CLI arguments pour flexibilité
- Variables d'environnement supportées

## Événements et Flux

### Cycle de Jeu
1. WebSocket détecte `status: 'starting'`
2. Historique récent analysé par la stratégie
3. Si signal d'achat: `BettingManager.place_bet()`
4. WebSocket détecte `status: 'crash'` avec crashpoint réel
5. Pari résolu (win/loss) et statistiques mises à jour

### Gestion des Erreurs
- Reconnexion automatique API
- Validations de balance avant pari
- Logging détaillé pour débogage
- Graceful shutdown

## Fichiers Générés

- `crash_history.csv` - Historique des jeux (game_id, timestamp, multiplier)
- `session_data/` - Données de session navigateur persistantes

## Exemple Complet

```bash
# Configuration pour trader agressif
python stake.py \
  --strategy high-after-low \
  --initial-balance 100.0 \
  --base-bet 2.0 \
  --target-multiplier 1.20 \
  --martingale-multiplier 1.5 \
  --max-martingale-steps 4

# Dans l'app:
# > info          # Affiche les stats
# > exit          # Quitter proprement
```

## Notes Importantes

⚠️ **Risques**
- Le pari comporte des risques financiers
- Aucune stratégie n'est garantie rentable
- Testez sur petit bankroll d'abord
- Surveillez toujours le martingale depth

💡 **Conseils**
- Utilisez `back_test.py` pour valider les stratégies sur historique
- Ajustez `max_martingale_steps` selon votre risk tolerance
- Commencez petit et augmentez progressivement
- Gardez des logs pour analyser la performance

## Extensibilité

Pour ajouter une nouvelle stratégie:

```python
class MaStrategie(Strategy):
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
    
    def should_bet(self, history: list[CrashRound]) -> bool:
        # Votre logique
        return condition
    
    def get_name(self) -> str:
        return "MaStrategie"
```

Puis modifier la fonction `main()` pour l'ajouter aux choices.

## Troubleshooting

**Q: WebSocket ne se connecte pas**
- Vérifiez la connexion internet
- Assurez-vous que Stake.com est accessible
- Vérifiez les logs pour les erreurs API

**Q: Erreur "Insufficient balance"**
- Le martingale montant dépasse le solde
- Réduisez `base_bet` ou `martingale_multiplier`
- Augmentez le solde initial

**Q: Strategy ne déclenche jamais**
- Vérifiez les paramètres de seuil
- Analysez `crash_history.csv` avec `back_test.py`
- Ajustez les thresholds

---

**Auteur**: Vanaty & AI Assistant  
**Date**: 2026-03-18  
**Version**: 2.0 (OOP Refactor)
