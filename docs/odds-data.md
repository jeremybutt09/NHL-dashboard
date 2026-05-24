# Odds & Fair-Value Data

## Current State: Stub Fixture

Live odds data is not yet sourced from a real provider. Instead, `nhl-dashboard/backend/odds_client.py` contains a deterministic fixture — `_MOCK` — a Python dict of 8 hardcoded odds entries keyed by game ID (1001–1008). The correct entry is selected by direct dict lookup on game ID, so every call is deterministic.

### Why a stub?

The devig math in `services/implied.py` is production-quality. The stub lets the full pipeline (fetch → store → compute fair value → display) run end-to-end while a real odds provider integration is deferred.

---

## `fetch_odds()` Interface

**File:** `nhl-dashboard/backend/odds_client.py`

**Function:** `fetch_odds(game_ids: list[int]) -> list[dict]`

Takes a list of game IDs and returns a list of odds dicts — one per game ID found in `_MOCK`. IDs not present in `_MOCK` are silently skipped.

### Return shape

Each dict in the returned list has this shape:

```python
# odds_client.py — fetch_odds() return shape (one entry per game)
{
    'game_id':       int,   # e.g. 1001
    'book':          str,   # always 'consensus' in stub
    'away_ml':       int,   # current American moneyline (e.g. 120 for +120)
    'home_ml':       int,   # current American moneyline (e.g. -140)
    'away_ml_open':  int,   # opening line
    'home_ml_open':  int,   # opening line
}
```

There are **8** hardcoded entries (game IDs 1001–1008), each with distinct odds ranges
(heavy favourites, coin-flip games, etc.) to give the UI variety during development.

> **No `implied`, `fair`, `edge`, or `movement_24h` keys are returned.** Implied
> probabilities are computed locally from the moneyline values by calling
> `american_to_implied()` inside `refresh_odds()` before inserting into `odds_snapshot`.
> Fair-value and edge are derived from the DB by the `compute_fair` scheduler job.

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

Rows older than 7 days are purged by the `prune` job (runs hourly) to keep the table size bounded.

### OddsSnapshot columns

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment row ID |
| `game_id` | Integer FK → `game.id` | Which game this snapshot belongs to |
| `fetched_at` | DateTime | UTC timestamp when the odds were recorded |
| `book` | String(32) | Odds source — **hardcoded to `'consensus'`** (see limitation below) |
| `away_ml` | Integer | Away American moneyline |
| `home_ml` | Integer | Home American moneyline |
| `away_implied` | Float | Away raw implied probability (computed from `away_ml`) |
| `home_implied` | Float | Home raw implied probability (computed from `home_ml`) |

### ModelFair columns

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | Integer PK FK → `game.id` | One row per game (upserted) |
| `away_fair` | Float | Away devigged fair probability (%) |
| `home_fair` | Float | Home devigged fair probability (%) |
| `computed_at` | DateTime | UTC timestamp of last computation |

---

## Current Limitation: `book` Column Hardcoded to `'consensus'`

The `book` column in `OddsSnapshot` is always written as `'consensus'` (see `scheduler.py::_poll_odds` → `refresh_odds()`). This means:

- All snapshots are treated as a single market view
- There is no per-book breakdown (DraftKings, FanDuel, BetMGM, etc.)
- Aggregation queries cannot separate line differences across books

This is fine for the MVP stub but will need addressing when a real odds source is integrated.

---

## To Replace the Stub

When you are ready to swap in a real odds provider, make the following changes:

### 1. Interface contract — what `fetch_odds(game_ids)` must return

The rest of the pipeline depends on this exact shape. Any real implementation **must** return a list of dicts, one per game, with at minimum:

```python
[
    {
        "game_id": int,          # the game ID passed in
        "book":    str,          # sportsbook identifier
        "away_ml": int,          # current American moneyline
        "home_ml": int,          # current American moneyline
    },
    ...
]
```

The keys `away_ml_open` and `home_ml_open` are optional; the scheduler only reads
`away_ml` and `home_ml` to compute implied probabilities. Include them if your
provider exposes them.

### 2. Files to edit

| File | Change |
|------|--------|
| `nhl-dashboard/backend/odds_client.py` | Replace `_MOCK` dict and the `fetch_odds()` function body with a real HTTP call to your odds provider. Keep the function signature `fetch_odds(game_ids: list[int]) -> list[dict]` unchanged. |
| `nhl-dashboard/backend/scheduler.py` | No changes needed — `_poll_odds()` already delegates to `refresh_odds()` in `services/slate.py`, which calls `fetch_odds()`. |

### 3. New columns for multi-book support

If you want to track odds from **multiple books** simultaneously, add to `OddsSnapshot`:

| New column | Suggested type | Purpose |
|------------|---------------|---------|
| `book` already exists | String(32) | Write the real book name instead of `'consensus'` |
| `away_ml_open` | Integer | Opening line per book (currently only in the fixture) |
| `home_ml_open` | Integer | Opening line per book |

No schema migration is needed for the `book` column — it already exists. Simply populate it with a real book identifier (e.g., `"draftkings"`, `"fanduel"`) instead of `"consensus"` and add a composite index on `(game_id, book, fetched_at)` for efficient per-book sparkline queries.
