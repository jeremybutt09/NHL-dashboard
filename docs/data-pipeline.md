# Data Pipeline: Background Jobs, Poll Intervals, and Data Flow

This document describes all background jobs that drive data writes to the NHL Dashboard database, their polling intervals, the tables they touch, and the end-to-end data flow from NHL API call to API response. Use it as the first stop when debugging data freshness or staleness issues.

---

## End-to-End Data Flow

```
NHL /v1/schedule/now
  └──> build_slate()          ──> team (upsert), game (upsert)

NHL /v1/gamecenter/{id}/boxscore
  └──> update_live_scores()   ──> game (update live fields only)

odds_client.get_odds() [stub fixture]
  └──> _poll_odds()           ──> odds_snapshot (insert-only / append)

odds_snapshot (latest per game)
  └──> _compute_fair()
         └──> devig_two_way() ──> model_fair (upsert)

odds_snapshot
  └──> prune_snapshots()      ──> DELETE rows WHERE fetched_at < now() − 7 days
```

Flask routes serve data from the database; no job bypasses the DB to return live API data directly.

---

## Scheduler Overview

All five jobs are registered in `nhl-dashboard/backend/scheduler.py` via APScheduler `BackgroundScheduler`. The scheduler is started in `create_app()` when `TESTING` is not set. Jobs run in threads that push a Flask application context before touching the database.

| Job ID | Trigger Interval | Function Called | Tables Written | Update Strategy |
|---|---|---|---|---|
| `poll_slate` | Every 5 minutes | `build_slate()` | `team`, `game` | Upsert (merge) |
| `poll_live` | Every 15 seconds | `update_live_scores()` | `game` | Update live fields only |
| `poll_odds` | Every 5 minutes | `_poll_odds()` (inline) | `odds_snapshot` | Insert-only (append) |
| `compute_fair` | Every 5 minutes | `_compute_fair()` (inline) | `model_fair` | Upsert |
| `prune_snapshots` | Every 1 hour | `prune_snapshots()` | `odds_snapshot` | Delete (age-based purge) |

---

## Job Details

### `poll_slate` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `build_slate()` in `services/slate.py`

**What it does:** Calls `GET /v1/schedule/now` on the NHL API, parses today's game list, and writes every team and game to the database. Uses `db.session.merge()` (SQLAlchemy's upsert-by-primary-key), so re-running the job never creates duplicate rows — it updates in place.

**Tables read:** none  
**Tables written:** `team` (upsert by `code`), `game` (upsert by `id`)  
**Update strategy:** Upsert (merge) — safe to run repeatedly

**Staleness signal:** If `game.updated_at` is more than ~6 minutes old, this job has likely stalled or the NHL API returned an error. Check `scheduler.get_last_poll()` — it returns the UTC timestamp of the last successful run.

---

### `poll_live` — Every 15 Seconds

**Source:** `nhl-dashboard/backend/scheduler.py` → `update_live_scores()` in `services/live.py`

**What it does:** Queries the database for games where `status = 'live'`, then calls `GET /v1/gamecenter/{id}/boxscore` for each. Writes `period`, `clock`, `away_score`, `home_score`, `away_sog`, `home_sog`, and `updated_at` back to the `game` row. No-ops if no games are live.

**Tables read:** `game` (filter by `status = 'live'`)  
**Tables written:** `game` (live columns only)  
**Update strategy:** Direct field update — does not upsert or insert

**Staleness signal:** If scores are stale during a live game, verify the `game.status` column is set to `'live'` by `poll_slate`. The live poller only operates on rows already marked live.

---

### `poll_odds` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `_poll_odds()` (defined inline)

**What it does:** For each game in the database, calls `odds_client.get_odds(game.id)` and inserts a new `OddsSnapshot` row with the current moneyline odds, implied probabilities, and a `fetched_at` timestamp. This is an **append-only** job — it never modifies existing rows, which preserves the full odds history for each game.

**Tables read:** `game` (to get the list of game IDs)  
**Tables written:** `odds_snapshot` (insert only)  
**Update strategy:** Insert-only / append

> **Stub state:** `odds_client.get_odds()` is currently a fixture that returns synthetic data. See `docs/odds-and-fair-value.md` for the real-API upgrade path.

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

```
Favorite (negative odds, e.g. -140):  implied = |odds| / (|odds| + 100) × 100
Underdog (positive odds, e.g. +120):  implied = 100 / (odds + 100) × 100
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

**Source:** `nhl-dashboard/backend/scheduler.py` → `prune_snapshots()` (top-level function)

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

To disable a job during development, comment out the corresponding `_scheduler.add_job(...)` call in `scheduler.py:init_scheduler()`. The scheduler itself must still start for the remaining jobs to run.

Alternatively, set `TESTING = True` in the app config — this skips `init_scheduler()` entirely and no background jobs run.

---

## Source Files

| File | Role |
|---|---|
| `nhl-dashboard/backend/scheduler.py` | All job definitions and registration |
| `nhl-dashboard/backend/services/slate.py` | `build_slate()` — schedule fetch and upsert |
| `nhl-dashboard/backend/services/live.py` | `update_live_scores()` — boxscore fetch and update |
| `nhl-dashboard/backend/services/implied.py` | `devig_two_way()`, `american_to_implied()`, `edge()` |
| `nhl-dashboard/backend/odds_client.py` | `get_odds()` — currently a stub fixture |
| `nhl-dashboard/backend/models.py` | SQLAlchemy models for all four tables |
