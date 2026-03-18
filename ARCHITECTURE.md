# Architecture & Class Diagram

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                                                                 │
│              STAKE CRASH PREDICTOR (Main Application)          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 StakeCrashPredictor                      │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • initialize()                                          │   │
│  │  • run()                                                 │   │
│  │  • handle_game_event()                                   │   │
│  │  • _place_bet()                                          │   │
│  │  • _display_stats()                                      │   │
│  └──┬─────────────────────────────────────────────────┬────┘   │
│     │                                                 │         │
│     ├─────────────────────────────────────────────────┼─────┐  │
│     │                                                 │     │  │
│  ┌──v─────────────────────┐  ┌──────────────────┐  ┌──v──────┐│
│  │  BrowserManager        │  │  StakeAPIClient  │  │ Betting ││
│  │  ────────────────────  │  │  ────────────────  │  │Manager ││
│  │ • initialize()         │  │ • fetch_graphql() │  │────────││
│  │ • close()              │  │ • fetch_user_     │  │• place_ ││
│  │ • navigate_to_game()   │  │   balance()      │  │  bet()  ││
│  │ • _setup_virtual_      │  │ • fetch_game_     │  │• resolve││
│  │   display()            │  │   hash()          │  │• _win() ││
│  │                        │  │ • fetch_crash_    │  │• resolve││
│  │ [Uses Playwright]      │  │   history()       │  │_loss() ││
│  └────────────────────────┘  └──────────────────┘  └─────────┘│
│          │                                              │       │
│  ┌───────v──────────────────────┐  ┌──────────────────v──────┐ │
│  │  GameHistoryManager          │  │  GamePredictionEngine    │ │
│  │  ───────────────────────────  │  │  ──────────────────────  │ │
│  │ • save_round()               │  │ • should_bet()           │ │
│  │ • get_recent_rounds()        │  │ • get_strategy_name()    │ │
│  │ • _initialize_file()         │  │                          │ │
│  │                              │  │ [Wraps Strategy]         │ │
│  │ [Persists to CSV]            │  └──────────┬───────────────┘ │
│  └──────────────────────────────┘             │                │
│                                               │                │
└───────────────────────────────────────────────┼────────────────┘
                                                │
                ┌───────────────────────────────v────────────────┐
                │                                                 │
                │          STRATEGY LAYER (Pluggable)            │
                │                                                 │
                │  ┌─────────────────────────────────────────┐   │
                │  │   Strategy (Abstract Base Class)        │   │
                │  │  ────────────────────────────────────  │   │
                │  │  • should_bet(history) [abstract]       │   │
                │  │  • get_name() [abstract]                │   │
                │  └──────────────────────────────────────────┘  │
                │         ▲              ▲              ▲         │
                │         │              │              │         │
                │   ┌─────┴──────┐  ┌───┴───────┐  ┌──┴──────┐   │
                │   │BetAfter    │  │LowStreak  │  │HighAfter│   │
                │   │Below       │  │Strategy   │  │LowStrat  │   │
                │   │Threshold   │  │           │  │          │   │
                │   │Strategy    │  │           │  │          │   │
                │   └────────────┘  └───────────┘  └──────────┘   │
                │                                                 │
                └─────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────┐
│   Stake.com WebSocket
│   (Game Events)     │
└──────────┬──────────┘
           │
           v
    ┌──────────────┐
    │ BrowserManager
    │  [Playwright]
    └──────┬───────┘
           │
           v
   ┌───────────────────────┐
   │  handle_game_event()  │
   └───────┬───────────────┘
           │
      ┌────┴────┐
      │          │
      v          v
  ┌─────────────────────┐  ┌──────────────────────┐
  │ Save Game History   │  │ Check if Should Bet  │
  │                     │  │                      │
  │GameHistoryManager   │  │GamePredictionEngine  │
  │.save_round()        │  │.should_bet()         │
  │    │                │  │    │                 │
  │    v                │  │    v                 │
  │ crash_history.csv   │  │ Strategy.should_bet()│
  └─────────────────────┘  │    │                 │
                           │    v                 │
                           │ True/False decision  │
                           └──────┬───────────────┘
                                  │
                          ┌───────┴────────┐
                          │                │
                         NO               YES
                          │                │
                          v                v
                    ┌──────────┐    ┌─────────────┐
                    │Continue  │    │_place_bet() │
                    │Listening │    │             │
                    └──────────┘    └──────┬──────┘
                                           │
                                           v
                                   ┌───────────────┐
                                   │BettingManager │
                                   │.place_bet()   │
                                   │               │
                                   │is_betting=True│
                                   │betting_amount │
                                   │martingale_step│
                                   └───────┬───────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
                    v                                             v
           ┌─────────────────┐                         ┌──────────────────┐
           │  Next Game      │                         │Resolve Previous  │
           │  Starts Event   │                         │  Bet Result      │
           │                 │                         │                  │
           │  Check Cashout  │                         │ If cashpoint >=  │
           │                 │                         │   target:        │
           │                 │                         │    resolve_win() │
           │                 │                         │                  │
           │                 │                         │ Else:            │
           │                 │                         │    resolve_loss()│
           └─────────────────┘                         │    martingale++  │
                                                       └──────────────────┘
                                                               │
                                                               v
                                                       ┌───────────────┐
                                                       │  Stats Update │
                                                       │               │
                                                       │balance updated│
                                                       │profit updated │
                                                       │wins/losses    │
                                                       └───────────────┘
```

---

## Class Dependency Graph

```
StakeCrashPredictor (Orchestrator)
    │
    ├─────────────────────────────────────────────┐
    │                                             │
    v                                             v
BrowserManager              StakeAPIClient
    │                              
    ├─> Playwright              
    │   ├─ chromium            
    │   └─ Page               
    │                          
    └─> Optional:             
        └─ pyvirtualdisplay    

StakeCrashPredictor
    │
    ├─────────────────────────────────────────────┐
    │                                             │
    v                                             v
BettingManager              GameHistoryManager
    │                              │
    ├─> BettingConfig              ├─> CrashRound[]
    │   ├─ initial_balance          │
    │   ├─ target_multiplier        └─> CSV File
    │   ├─ base_bet                    (crash_history.csv)
    │   ├─ martingale_multiplier
    │   └─ max_martingale_steps

StakeCrashPredictor
    │
    └─────────────────────────────────────────────┐
                                                  │
                                                  v
                                    GamePredictionEngine
                                                  │
                                                  v
                                              Strategy (ABC)
                                                  │
                            ┌─────────────────────┼─────────────────────┐
                            │                     │                     │
                            v                     v                     v
              BetAfterBelow     LowStreakStrategy   HighAfterLow
              ThresholdStrategy                     Strategy
                            
```

---

## State Machine Diagram

```
┌──────────────────────────────────────┐
│      APPLICATION STATES              │
└──────────────────────────────────────┘

                ┌────────────┐
                │  START     │
                └─────┬──────┘
                      │
                      v
                ┌─────────────┐
            ┌──>│INITIALIZING │<──┐
            │   └──────┬──────┘   │
            │          │          │
            │          v          │
            │   ┌──────────────┐  │
            │   │ Connecting   │  │
            │   │ to Browser   │  │
            │   └──────┬───────┘  │
            │          │          │
            │          v          │
            │   ┌───────────────┐ │
            └───│ Fetching User │ │ ERROR
                │ Data          │ │
                └───┬───────────┘ │
                    │             │
                    v             │
            ┌──────────────────┐  │
            │LISTENING          │──┘ Retry
            │(Ready for events) │
            └────┬─────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        v                 v
    GAME_STARTING    PREDICTING
        │                 │
        │            (Check history)
        │                 │
        │            ┌────v─────────┐
        │            │ShouldBet?    │
        │            └────┬────┬────┘
        │                 │    │
        │            YES  │    │  NO
        │                 │    │
        │            ┌────v──┐ │
        │            │PLACING│ │
        │            │BET    │ │
        │            └────┬──┘ │
        │                 │    │
        v                 v    v
    GAME_CRASHING -> RESOLVING <- (Continue listening)
        │
        │ (Result received)
        │
        ├─── WIN ──────┐
        │              v
        │         PROFIT_CALCULATION
        │              │
        └─── LOSS ──┐  │
                    v  │
              MARTINGALE_CHECK
                    │
        ┌───────────┴────────────┐
        │                        │
        v                        v
    RESET               MAX_STEPS_REACHED?
        │                        │
        │                  ┌─────┴─────┐
        │                  │           │
        └──────┬───────────>v           v
               │      CONTINUE    RESET_ALL
               │         │            │
               └─────────┼────────────┘
                         v
                 ┌───────────────┐
                 │LISTENING      │
                 │(back to top)  │
                 └───────────────┘
```

---

## Configuration Object Model

```
┌──────────────────────────────────────┐
│      BettingConfig (dataclass)       │
├──────────────────────────────────────┤
│ Attributes:                          │
│                                      │
│ • initial_balance: float             │
│   Default: 9.27                      │
│   Usage: Starting bankroll           │
│                                      │
│ • target_multiplier: float           │
│   Default: 1.09                      │
│   Usage: Cashout multiplier          │
│                                      │
│ • base_bet: float                    │
│   Default: 1.0                       │
│   Usage: First bet amount            │
│                                      │
│ • martingale_multiplier: float       │
│   Default: 11.65                     │
│   Usage: Bet escalation factor       │
│                                      │
│ • max_martingale_steps: int          │
│   Default: 3                         │
│   Usage: Reset after N losses        │
│                                      │
└──────────────────────────────────────┘
           │
           │ Injected into
           v
┌──────────────────────────────────────┐
│    StakeCrashPredictor               │
│    __init__(strategy, config)        │
└──────────────────────────────────────┘
           │
           │ Passed to
           v
┌──────────────────────────────────────┐
│    BettingManager                    │
│    __init__(config)                  │
│                                      │
│ Uses config to initialize:           │
│ • balance = initial_balance          │
│ • betting logic                      │
│ • martingale calculations            │
└──────────────────────────────────────┘
```

---

## Strategy Pattern Implementation

```
┌─────────────────────────────────────────────────────┐
│           Strategy (ABC Interface)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  @abstractmethod                                    │
│  def should_bet(history: list[CrashRound]) -> bool │
│                                                     │
│  @abstractmethod                                    │
│  def get_name() -> str                              │
│                                                     │
└─────────────────────────────────────────────────────┘
        ▲               ▲                  ▲
        │               │                  │
        │               │                  │
    Implements      Implements         Implements
        │               │                  │
        │               │                  │
┌───────┴──────────┐ ┌──────────────────────────┐
│                  │ │                          │
v                  v v                          v
BetAfter       LowStreak               HighAfterLow
BelowThresholdStrategy                Strategy
Strategy
         │              │                  │
         │              │                  │
         v              v                  v
    ┌────────────┐ ┌──────────────┐ ┌─────────────┐
    │if crash <  │ │if N recent   │ │if recent <  │
    │threshold:  │ │crashes <=    │ │avg * (1-    │
    │  return    │ │trigger       │ │drop):       │
    │  True      │ │threshold:    │ │  return     │
    │            │ │  return      │ │  True       │
    │            │ │  True        │ │             │
    └────────────┘ └──────────────┘ └─────────────┘

    Usage:
    ──────
    strategy = BetAfterBelowThresholdStrategy(threshold=1.01)
    engine = GamePredictionEngine(strategy)
    
    if engine.should_bet(history):
        predictor._place_bet()
```

---

## Event Loop Flow

```
┌─────────────────────────────────────┐
│   Main Application Loop             │
└────────────────┬────────────────────┘
                 │
                 v
        ┌────────────────┐
        │ await run()    │
        └────────┬───────┘
                 │
                 v
        ┌────────────────────────┐
        │ await initialize()     │
        ├────────────────────────┤
        │ • Init browser         │
        │ • Create API client    │
        │ • Init betting mgr     │
        │ • Navigate to game     │
        └────────┬───────────────┘
                 │
                 v
        ┌────────────────────────┐
        │ Setup WebSocket Handler│
        │                        │
        │ page.on("websocket",   │
        │   lambda ws: ...)      │
        └────────┬───────────────┘
                 │
                 v
        ┌────────────────────────┐
        │   INTERACTIVE LOOP     │
        │                        │
        │ while self.running:   │
        │   input > user_cmd    │
        │   if cmd == "info":   │
        │     _display_stats()  │
        │   elif cmd == "exit": │
        │     self.running=False│
        └────────┬───────────────┘
                 │
                 v
        ┌────────────────────────┐
        │ WebSocket Listener     │
        │ (concurrent)           │
        │                        │
        │ on "framereceived":   │
        │  handle_game_event()  │
        │    ├─ Update history  │
        │    ├─ Resolve bet     │
        │    └─ Predict next    │
        └────────┬───────────────┘
                 │
                 v
        ┌────────────────────────┐
        │ finally:               │
        │ await browser.close()  │
        └────────────────────────┘
```

---

## Database Schema (CSV)

```
crash_history.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Columns:
  [0] game_id       (string)   - Unique game identifier
  [1] timestamp     (ISO8601)  - When crash occurred
  [2] multiplier    (float)    - Crash multiplier value

Example Rows:
  ┌─────────────────────────────────────────────────┐
  │game_id,timestamp,multiplier                    │
  │game_12345,2026-03-18T15:30:45+00:00,2.45      │
  │game_12346,2026-03-18T15:31:15+00:00,1.02      │
  │game_12347,2026-03-18T15:32:00+00:00,5.67      │
  │game_12348,2026-03-18T15:32:45+00:00,1.00      │
  │game_12349,2026-03-18T15:33:30+00:00,3.21      │
  └─────────────────────────────────────────────────┘

Data Type Definitions:
  ┌────────────────────────────────────────────┐
  │@dataclass                                  │
  │class CrashRound:                           │
  │  game_id: str                              │
  │  timestamp: str                            │
  │  multiplier: float                         │
  └────────────────────────────────────────────┘
```

---

## Testing Architecture (Future)

```
┌──────────────────────────────────────────────────┐
│         Unit Tests (pytest)                      │
├──────────────────────────────────────────────────┤
│                                                  │
│ test_strategies.py                               │
│  • test_bet_after_below_threshold()              │
│  • test_low_streak_strategy()                    │
│  • test_high_after_low_strategy()                │
│                                                  │
│ test_betting_manager.py                          │
│  • test_place_bet()                              │
│  • test_resolve_win()                            │
│  • test_resolve_loss()                           │
│  • test_martingale_calculation()                 │
│                                                  │
│ test_game_history.py                             │
│  • test_save_round()                             │
│  • test_get_recent_rounds()                      │
│                                                  │
└──────────────────────────────────────────────────┘
                    │
                    v
        ┌──────────────────────────┐
        │ Integration Tests        │
        │                          │
        │ • Mock Stake API         │
        │ • Mock WebSocket         │
        │ • Test event flow        │
        └──────────────────────────┘
                    │
                    v
        ┌──────────────────────────┐
        │ E2E Tests (Manual)       │
        │                          │
        │ • Live on test account   │
        │ • Monitor performance    │
        │ • Validate results       │
        └──────────────────────────┘
```

---

## CLI Architecture

```
┌─────────────────────────────────────────────────┐
│           Command Line Interface                │
│  (argparse with 19 options)                     │
└────────────────┬────────────────────────────────┘
                 │
                 v
        ┌────────────────────────┐
        │ Parse Arguments        │
        │ ──────────────────────│
        │ • strategy             │
        │ • initial-balance      │
        │ • base-bet             │
        │ • target-multiplier    │
        │ • martingale-*         │
        │ • entry-threshold      │
        │ • trigger-threshold    │
        │ • trigger-streak       │
        │ • pyvirtual (flag)     │
        └────────────┬───────────┘
                     │
        ┌────────────v──────────────┐
        │ Create Config Object      │
        │  ──────────────────────   │
        │ BettingConfig(            │
        │   initial_balance=...,    │
        │   base_bet=...,           │
        │   ...                     │
        │ )                         │
        └────────────┬──────────────┘
                     │
        ┌────────────v──────────────────┐
        │ Create Strategy Object       │
        │  ────────────────────────── │
        │ if strategy == "after-below":│
        │   BetAfterBelow...(...)      │
        │ elif strategy == "low-streak"│
        │   LowStreakStrategy(...)     │
        │ else:                        │
        │   HighAfterLow(...)          │
        └────────────┬──────────────────┘
                     │
        ┌────────────v──────────────────┐
        │ Create Predictor             │
        │  ────────────────────────── │
        │ predictor = StakeCrash      │
        │   Predictor(                │
        │     strategy=strategy,       │
        │     config=config,           │
        │     enable_pyvirtual=pyvirt) │
        └────────────┬──────────────────┘
                     │
                     v
        ┌────────────────────────┐
        │ await predictor.run()  │
        │                        │
        │ (See Event Loop)       │
        └────────────────────────┘
```

---

## Summary

This architecture provides:

✅ **Modularity** - Each component has single responsibility  
✅ **Extensibility** - Easy to add new strategies  
✅ **Maintainability** - Clear separation of concerns  
✅ **Testability** - Components can be tested in isolation  
✅ **Flexibility** - Configuration injected, not hardcoded  
✅ **Scalability** - Ready for multi-strategy deployment  

---

*Architecture Documentation Complete* ✅
