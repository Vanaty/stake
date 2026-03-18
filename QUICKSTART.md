# Quick Start Guide - Stake Crash Predictor

## 🚀 Démarrage Rapide (5 minutes)

### Étape 1: Installation
```bash
pip install patchright
# Optionnel:
pip install pyvirtualdisplay
```

### Étape 2: Lancer l'App
```bash
# Utiliser les paramètres par défaut
python stake.py

# Ou personnaliser:
python stake.py --strategy after-below --base-bet 1.0 --initial-balance 10.0
```

### Étape 3: Interagir
```
Commandes: 'info' (stats), 'exit' (quitter) > info
==================================================
Stratégie: BetAfterBelowThreshold(threshold=1.01)
Solde: 9.27 USDC
Profit total: 0.00 USDC
Nombre de paris: 0
Victoires/Pertes: 0/0
Taux de réussite: 0.00%
Pas martingale actuel: 0/3
==================================================

Commandes: 'info' (stats), 'exit' (quitter) > exit
```

---

## 📚 Choisir une Stratégie

### Pour Débuter (Faible Risque)
```bash
python stake.py --strategy after-below \
                --initial-balance 10.0 \
                --base-bet 0.5
```
**Quand parie**: Après un crash très bas (< 1.01x)  
**Risque**: Bas | **Fréquence**: Basse | **Profit/Pari**: Petit

### Intermédiaire (Risque Modéré)
```bash
python stake.py --strategy low-streak \
                --trigger-threshold 2.0 \
                --trigger-streak 3 \
                --initial-balance 25.0 \
                --base-bet 1.0
```
**Quand parie**: Après 3 crashes faibles consécutifs  
**Risque**: Modéré | **Fréquence**: Modérée | **Profit/Pari**: Moyen

### Avancé (Risque Élevé)
```bash
python stake.py --strategy high-after-low \
                --initial-balance 100.0 \
                --base-bet 2.0 \
                --target-multiplier 1.20 \
                --martingale-multiplier 3.0
```
**Quand parie**: Après une baisse de la moyenne  
**Risque**: Élevé | **Fréquence**: Haute | **Profit/Pari**: Élevé

---

## 🔧 Paramètres Importants

### Balance & Mise
```
--initial-balance 50.0      # Bankroll de départ
--base-bet 1.0             # Première mise
```
**Conseil**: `base_bet` ≤ `initial_balance / 50`

### Multiplicateur Cible
```
--target-multiplier 1.09   # Pour cashout à 1.09x
```
**Plus bas** = Plus sûr | **Plus haut** = Plus risqué

### Martingale (Progression)
```
--martingale-multiplier 2.0     # Doubler la mise à chaque perte
--max-martingale-steps 3        # Max 3 niveaux (reset après)
```

**Exemple Martingale**:
```
Pari 1: 1.0 USDC
Perte ❌ → Pari 2: 2.0 USDC (1 × 2)
Perte ❌ → Pari 3: 4.0 USDC (2 × 2)
Perte ❌ → Reset à 1.0 USDC
```

---

## 📊 Monitorer la Performance

### Afficher les stats
```
> info
```

**Métriques importantes**:
- **Taux de réussite**: > 50% = Profitable
- **Hit rate**: Fréquence des paris gagnants
- **Profit total**: Évolution du bankroll

### Sauvegarder les données
Les rounds sont auto-sauvegardés dans `crash_history.csv`.

Analyser avec backtest:
```bash
python back_test.py --csv crash_history.csv \
                   --strategy after-below \
                   --entry-threshold 1.01 \
                   --bankroll 9.27 \
                   --bet 1.0 \
                   --target 1.09
```

---

## ⚠️ Gestion du Risque

### Golden Rules
1. **Commencer petit** - Begin with minimum bets
2. **Tester en backtest** - Validate strategy first
3. **Limiter martingale** - Max 3-4 steps
4. **Monitorer l'application** - Ne pas laisser sans surveillance
5. **Stop-loss mental** - Décider de l'arrêt à l'avance

### Risk Calculation
```
Max Loss = Base Bet × (Multiplicateur^Niveaux - 1) / (Multiplicateur - 1)

Exemple: base=1, mult=2, levels=3
Max Loss = 1 × (2^3 - 1) = 7 USDC
```

Assurez-vous que `Initial Balance >> Max Loss`

---

## 🐛 Troubleshooting

### L'app ne démarre pas
```
Error: patchright not found
→ Installer: pip install patchright
```

### WebSocket ne se connecte pas
```
Error: Cannot reach https://stake.com
→ Vérifier connexion internet
→ Vérifier que Stake.com est accessible
```

### Pari n'est jamais placé
```
→ Vérifier la stratégie avec: > info
→ Analyser crash_history.csv
→ Ajuster les seuils
```

### Balance change sans pari
```
→ Vérifier logs pour WebSocket errors
→ Redémarrer l'app
→ Vérifier directement sur Stake.com
```

---

## 📈 Optimisation

### Backtester avant de live
```bash
# Tester une stratégie sur l'historique
python back_test.py --strategy after-below \
                   --entry-threshold 1.02 \
                   --bankroll 100 \
                   --bet 1.0
```

### Ajuster par expérimentation
1. Backtester 10+ combinaisons
2. Identifier la meilleure
3. Lancer 1-2h en live
4. Si profitable → augmenter légèrement base_bet
5. Si losses → réduit bet ou ajuste threshold

---

## 🎯 Scénarios Courants

### Scénario 1: "Je veux tester sans risque"
```bash
python stake.py --initial-balance 1.0 --base-bet 0.01
# Simule avec micro-mises
```

### Scénario 2: "Je veux un revenu passif stable"
```bash
python stake.py --strategy after-below \
                --initial-balance 200 \
                --base-bet 2.0 \
                --target-multiplier 1.05 \
                --martingale-multiplier 1.3 \
                --max-martingale-steps 3
```

### Scénario 3: "Je veux maximiser les profits"
```bash
python stake.py --strategy high-after-low \
                --initial-balance 500 \
                --base-bet 5.0 \
                --target-multiplier 1.25 \
                --martingale-multiplier 4.0 \
                --max-martingale-steps 2
```

### Scénario 4: "Je veux apprendre"
```bash
# Regarder les logs + statistiques
python stake.py --strategy low-streak
# > info (toutes les few minutes)
# Vérifier crash_history.csv
```

---

## 💡 Pro Tips

**Tip 1**: La meilleure stratégie dépend des patterns locaux
- Collector 100+ rounds de données
- Tester toutes les stratégies
- Choisir celle avec le meilleur ROI

**Tip 2**: Martingale est dangereux
- 3-4 niveaux max
- Risque de ruine = perte totale du bankroll
- Utiliser comme "filet de sécurité" seulement

**Tip 3**: Temps de jeu
- Stake Crash est rapide (30s par round)
- Vérifier périodiquement (toutes les heures)
- Laisser tourner max 4-8 heures/jour

**Tip 4**: Gestion mentale
- Ne pas devenir émotif
- Respecter la stratégie sans dévier
- Accepter les pertes comme normales

---

## 📞 Support

### Logs détaillés
```bash
# L'application loggue tout automatiquement en couleur
# DEBUG = logique interne
# INFO = événements importants
# WARNING = Attention requise
# SUCCESS = Pari gagné
# ERROR = Problème majeur
```

### Analyser l'historique
```bash
# CSV format: game_id,timestamp,multiplier
cat crash_history.csv | head -20
```

---

## ✨ Résumé

| Aspect | Action |
|--------|--------|
| **Démarrer** | `python stake.py` |
| **Backtester** | `python back_test.py` |
| **Monitorer** | Appuyez sur `info` |
| **Quitter** | Appuyez sur `exit` |
| **Analyser** | Regarder `crash_history.csv` |

---

**Bonne chance! 🍀**

*Remember: House edge existe. Pas de stratégie garantie.*
