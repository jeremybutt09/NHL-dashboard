# Odds & Fair-Value Data

## Current State: Stub Fixture

Live odds data is not yet sourced from a real provider. Instead, `nhl-dashboard/backend/odds_client.py` contains a deterministic fixture — `_SLATE_ODDS` — with 8 hardcoded odds sets. The correct set is selected via `game_id % 8`, so every call is deterministic and different game IDs produce visually distinct rows.

### Why a stub?

The devig math in `services/implied.py` is production-quality. The stub lets the full pipeline (fetch → store → compute fair value → display) run end-to-end while a real odds provider integration is deferred.

---

## Fixture Structure

`get_odds(game_id)` returns one entry from `_SLATE_ODDS`, selected by `game_id % len(_SLATE_ODDS)`:

```python
# odds_client.py — get_odds() return shape
{
    "ml":          {"away": 120,   "home": -140},   # current American moneyline
    "ml_open":     {"away": 115,   "home": -135},   # opening line
    "implied":     {"away": 45.0,  "home": 55.0},   # raw implied probabilities (%)
    "fair":        {"away": 47.5,  "home": 52.5},   # devigged fair value (%)
    "edge":        2.1,                              # fair − market (pp)
    "movement_24h": [46.38, 44.95, ..., 45.0],      # 24-point sparkline array
}
```

There are **8** hardcoded sets, each with distinct odds ranges (heavy favourites, coin-flip games, etc.) to give the UI variety during development.

---

## Math: american_to_implied()

**File:** `nhl-dashboard/backend/services/implied.py`

American moneyline odds carry an embedded probability. The formula differs by sign:

| Sign | Formula | Example |
|------|---------|---------|
| Positive (`+120`) | `100 / (odds + 100) × 100` | `100 / 220 × 100 = 45.45%` |
| Negative (`-140`) | `abs(odds) / (abs(odds) + 100) × 100` | `140 / 240 × 100 = 58.33%` |

Because a sportsbook charges vig, the away and home probabilities from a real line will sum to **more than 100** (e.g., 103–106%). `american_to_implied` only converts; it does not remove the vig.

---

## Math: devig_two_way()

**File:** `nhl-dashboard/backend/services/implied.py`

The vig inflates the sum of implied probabilities. `devig_two_way` normalises both sides so they sum to exactly 100, giving the book's "true" estimate of each outcome.

```
total      = away_implied + home_implied   # e.g. 45.5 + 58.3 = 103.8  (vig = 3.8%)
away_fair  = away_implied / total × 100   # 45.5 / 103.8 × 100 = 43.8%
home_fair  = home_implied / total × 100   # 58.3 / 103.8 × 100 = 56.2%
```

The results represent the market's fair probability with the bookmaker's margin removed.

---

## OddsSnapshot: Append-Only Time-Series Design

**Model:** `nhl-dashboard/backend/models.py` (`OddsSnapshot` → table `odds_snapshot`)

Every time `_poll_odds` runs (every 5 minutes), it inserts a **new row** into `odds_snapshot` for each game rather than updating an existing one. This append-only design preserves odds history so the frontend can render:

- **24-hour sparklines** showing how the line has moved throughout the day
- **Trend views** identifying sharp line movement before game time

Rows older than 7 days are purged by the `prune_snapshots` job (runs hourly) to keep the table size bounded.

### OddsSnapshot columns

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment row ID |
| `game_id` | Integer FK → `game.id` | Which game this snapshot belongs to |
| `fetched_at` | DateTime | UTC timestamp when the odds were recorded |
| `book` | String(32) | Odds source — **hardcoded to `'consensus'`** (see limitation below) |
| `away_ml` | Integer | Away American moneyline |
| `home_ml` | Integer | Home American moneyline |
| `away_implied` | Float | Away raw implied probability (%) |
| `home_implied` | Float | Home raw implied probability (%) |

### ModelFair columns

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | Integer PK FK → `game.id` | One row per game (upserted) |
| `away_fair` | Float | Away devigged fair probability (%) |
| `home_fair` | Float | Home devigged fair probability (%) |
| `computed_at` | DateTime | UTC timestamp of last computation |

---

## Current Limitation: `book` Column Hardcoded to `'consensus'`

The `book` column in `OddsSnapshot` is always written as `'consensus'` (see `scheduler.py::_poll_odds`). This means:

- All snapshots are treated as a single market view
- There is no per-book breakdown (DraftKings, FanDuel, BetMGM, etc.)
- Aggregation queries cannot separate line differences across books

This is fine for the MVP stub but will need addressing when a real odds source is integrated.

---

## To Replace the Stub

When you are ready to swap in a real odds provider, make the following changes:

### 1. Interface contract — what `get_odds(game_id)` must return

The rest of the pipeline depends on this exact shape. Any real implementation **must** return a dict with these keys:

```python
{
    "ml":      {"away": int,   "home": int},    # current American moneyline
    "implied": {"away": float, "home": float},  # raw implied probabilities (%)
}
```

The keys `ml_open`, `fair`, `edge`, and `movement_24h` are optional; the scheduler only reads `ml` and `implied`. If your provider exposes those extras you may include them, but they are not required.

### 2. Files to edit

| File | Change |
|------|--------|
| `nhl-dashboard/backend/odds_client.py` | Replace `_SLATE_ODDS` fixture and the `get_odds()` function body with a real HTTP call to your odds provider. Keep the function signature `get_odds(game_id: int) -> dict` unchanged. |
| `nhl-dashboard/backend/scheduler.py` | No changes needed — `_poll_odds` already calls `get_odds(game.id)` and stores the result. |

### 3. New columns for multi-book support

If you want to track odds from **multiple books** simultaneously, add to `OddsSnapshot`:

| New column | Suggested type | Purpose |
|------------|---------------|---------|
| `book` already exists | String(32) | Write the real book name instead of `'consensus'` |
| `away_ml_open` | Integer | Opening line per book (currently only in the fixture) |
| `home_ml_open` | Integer | Opening line per book |

No schema migration is needed for the `book` column — it already exists. Simply populate it with a real book identifier (e.g., `"draftkings"`, `"fanduel"`) instead of `"consensus"` and add a composite index on `(game_id, book, fetched_at)` for efficient per-book sparkline queries.
