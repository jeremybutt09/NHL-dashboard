# Data Pipeline: Background Jobs, Poll Intervals, and Data Flow

This document describes all background jobs that drive data writes to the NHL Dashboard database, their polling intervals, the tables they touch, and the end-to-end data flow from NHL API call to API response. Use it as the first stop when debugging data freshness or staleness issues.

---

## End-to-End Data Flow

```
NHL /v1/schedule/now
  └──> refresh_slate()        ──> team (upsert), game (upsert)

NHL /v1/gamecenter/{id}/boxscore
  └──> refresh_live()         ──> game (update live fields only)

fetch_odds() [stub fixture]
  └──> refresh_odds()
         └──> _poll_odds()    ──> odds_snapshot (insert-only / append)

odds_snapshot (latest per game)
  └──> _compute_fair()
         └──> devig_two_way() ──> model_fair (upsert)

odds_snapshot
  └──> _prune_snapshots()
         └──> prune_old_snapshots() ──> DELETE rows WHERE fetched_at < now() − 7 days
```

Flask routes serve data from the database; no job bypasses the DB to return live API data directly.

---

## Scheduler Overview

All five jobs are registered in `nhl-dashboard/backend/scheduler.py` via APScheduler `BackgroundScheduler`. The scheduler is started via `start_scheduler(app)`, which is called from `create_app()` when `TESTING` is not set. Jobs run in threads that push a Flask application context before touching the database.

| Job ID | Trigger Interval | Function Called | Tables Written | Update Strategy |
|---|---|---|---|---|
| `poll_slate` | Every 5 minutes | `refresh_slate()` in `services/slate.py` | `team`, `game` | Upsert (`db.session.get()` + `add()`) |
| `poll_live` | Every 15 seconds | `refresh_live()` in `services/live.py` | `game` | Update live fields only |
| `poll_odds` | Every 5 minutes | `_poll_odds()` → `refresh_odds()` | `odds_snapshot` | Insert-only (append) |
| `compute_fair` | Every 5 minutes | `_compute_fair()` (inline) | `model_fair` | Upsert |
| `prune` | Every 1 hour | `_prune_snapshots()` → `prune_old_snapshots()` | `odds_snapshot` | Delete (age-based purge) |

---

## Job Details

### `poll_slate` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_slate()` in `services/slate.py`

**What it does:** Calls `GET /v1/schedule/now` on the NHL API, parses today's game list, and writes every team and game to the database. Uses `db.session.get()` to look up each row by primary key, then `db.session.add()` for new rows — equivalent to an upsert. Re-running the job never creates duplicate rows; it updates in place.

**Tables read:** none  
**Tables written:** `team` (upsert by `code`), `game` (upsert by `id`)  
**Update strategy:** Upsert (`db.session.get()` + `db.session.add()`) — safe to run repeatedly

**Staleness signal:** If `game.updated_at` is more than ~6 minutes old, this job has likely stalled or the NHL API returned an error.

---

### `poll_live` — Every 15 Seconds

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_live()` in `services/live.py`

**What it does:** Queries the database for games where `status = 'live'`, then calls `GET /v1/gamecenter/{id}/boxscore` for each. Writes `period`, `clock`, `away_score`, `home_score`, `away_sog`, `home_sog`, and `updated_at` back to the `game` row. No-ops if no games are live.

**Tables read:** `game` (filter by `status = 'live'`)  
**Tables written:** `game` (live columns only)  
**Update strategy:** Direct field update — does not upsert or insert

**Staleness signal:** If scores are stale during a live game, verify the `game.status` column is set to `'live'` by `poll_slate`. The live poller only operates on rows already marked live.

---

### `poll_odds` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `_poll_odds()` (delegates to `refresh_odds()` in `services/slate.py`)

**What it does:** `_poll_odds()` calls `refresh_odds()`, which calls `fetch_odds(game_ids)` from `odds_client.py` to retrieve mock odds for the demo game IDs. A new `OddsSnapshot` row is inserted for each result with the current moneyline odds and a `fetched_at` timestamp. This is an **append-only** job — it never modifies existing rows, which preserves the full odds history for each game.

**Tables read:** none (uses hardcoded demo IDs from `odds_client._MOCK`)  
**Tables written:** `odds_snapshot` (insert only)  
**Update strategy:** Insert-only / append

> **Stub state:** `odds_client.fetch_odds()` returns data from the `_MOCK` dict (deterministic fixture). See `docs/odds-data.md` for the real-API upgrade path.

---

### `compute_fair` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `_compute_fair()` (defined inline)

**What it does:** For each game, fetches the most recent `OddsSnapshot` row (ordered by `fetched_at DESC`), runs the devig computation, and upserts the result into `model_fair`. Skips games with no snapshot yet.

**Tables read:** `game`, `odds_snapshot` (latest per game)  
**Tables written:** `model_fair` (upsert by `game_id`)  
**Update strategy:** Upsert — creates a `ModelFair` row on first run, updates it on subsequent runs

#### `model_fair` Computation — Devig Formula

The raw implied probabilities stored in `odds_snapshot` (e.g. `away_implied = 52.4`, `home_implied = 50.0`) sum to more than 100 because the sportsbook embeds a vig (margin). The devig step removes the vig so the two probabilities sum to exactly 100, yielding the model's estimate of true win probability.

**Step 1 — Convert American odds to implied probability** (`american_to_implied` in `services/implied.py`):

Returns **percentage points (0–100)**. e.g. `-110` → `52.38`, not `0.5238`.

```
Favorite (negative odds, e.g. -140):  implied = |odds| / (|odds| + 100) × 100  →  e.g. 58.33
Underdog (positive odds, e.g. +120):  implied = 100 / (odds + 100) × 100        →  e.g. 45.45
```

**Step 2 — Normalize via `devig_two_way`** (`services/implied.py`):

```
total = p_away + p_home          # e.g. 52.4 + 50.0 = 102.4
away_fair = p_away / total × 100  # 52.4 / 102.4 × 100 ≈ 51.17
home_fair = p_home / total × 100  # 50.0 / 102.4 × 100 ≈ 48.83
```

The resulting `away_fair` and `home_fair` values (stored in `model_fair`) sum to 100 and represent the model's fair-value win probabilities, free of the bookmaker's vig.

**Inputs:** `odds_snapshot.away_implied`, `odds_snapshot.home_implied`  
**Outputs:** `model_fair.away_fair`, `model_fair.home_fair`, `model_fair.computed_at`

---

### `prune_snapshots` — Every 1 Hour

**Source:** `nhl-dashboard/backend/scheduler.py` → `_prune_snapshots()` wrapper → `prune_old_snapshots()` in `services/slate.py`

**APScheduler job ID:** `prune`

**What it does:** Deletes all `OddsSnapshot` rows where `fetched_at` is older than 7 days. This prevents unbounded table growth while retaining enough history for short-term odds-movement analysis.

**Tables read:** none  
**Tables written:** `odds_snapshot` (hard delete)  
**Update strategy:** Age-based purge — `DELETE WHERE fetched_at < now() − 7 days`

**Retention policy:** 7-day rolling window, purged hourly.

---

## Local Development Guidance

Not all jobs are equally necessary for local development. The table below indicates which jobs are safe to disable:

| Job ID | Safe to Disable Locally? | Notes |
|---|---|---|
| `poll_slate` | **No** — required for data | Must run at least once to populate `game` and `team` tables |
| `poll_live` | Yes | No-ops when no games are live; disable to reduce noise |
| `poll_odds` | Yes (with stub) | Stub returns fixture data; disable if you don't need odds snapshots |
| `compute_fair` | Yes | Skips gracefully when no snapshots exist |
| `prune_snapshots` | Yes | No functional impact during short dev sessions |

To disable a job during development, comment out the corresponding `_scheduler.add_job(...)` call in `scheduler.py:start_scheduler()`. The scheduler itself must still start for the remaining jobs to run.

Alternatively, set `TESTING = True` in the app config — this skips `start_scheduler()` entirely and no background jobs run.

---

## Source Files

| File | Role |
|---|---|
| `nhl-dashboard/backend/scheduler.py` | All job definitions and registration; `start_scheduler(app)` entry point |
| `nhl-dashboard/backend/services/slate.py` | `refresh_slate()` — schedule fetch and upsert; `refresh_odds()` — odds snapshot insert; `prune_old_snapshots()` — age purge |
| `nhl-dashboard/backend/services/live.py` | `refresh_live()` — boxscore fetch and update |
| `nhl-dashboard/backend/services/implied.py` | `devig_two_way()`, `american_to_implied()`, `edge()` |
| `nhl-dashboard/backend/odds_client.py` | `fetch_odds(game_ids)` — currently a stub fixture |
| `nhl-dashboard/backend/models.py` | SQLAlchemy models for all four tables |
