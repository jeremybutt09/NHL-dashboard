# Data Pipeline: Background Jobs, Poll Intervals, and Data Flow

This document describes all background jobs that drive data writes to the NHL Dashboard database, their polling intervals, the tables they touch, and the end-to-end data flow from NHL API call to API response. Use it as the first stop when debugging data freshness or staleness issues.

---

## End-to-End Data Flow

```
NHL /v1/schedule/now
  └──> refresh_schedule()  ──> team (upsert), live_game (upsert)

NHL /v1/score/now
  └──> refresh_scores()    ──> live_game (update live fields + status)

NHL /v1/gamecenter/{id}/boxscore
  └──> refresh_boxscores() ──> boxscore (upsert by game_id)

boxscore (today's rows)
  └──> refresh_dashboard_games() ──> dashboard_game (upsert by game_id)

fetch_odds() [stub fixture]
  └──> refresh_odds()
         └──> _poll_odds() ──> odds_snapshot (insert-only / append)

odds_snapshot (latest per game)
  └──> compute_all_fair()
         └──> devig_two_way() ──> model_fair (upsert)

odds_snapshot
  └──> prune_old_snapshots() ──> DELETE rows WHERE fetched_at < now() − 7 days

NHL stats/rest/en/game (full historical set)
  └──> refresh_recent_historical_games()  ──> game (upsert by game_id, 30-day window)
  └──> ingest_historical_games()          ──> game (full backfill upsert)
```

Flask routes serve data from the database; no job bypasses the DB to return live API data directly.

---

## Scheduler Overview

All jobs are registered in `nhl-dashboard/backend/scheduler.py` via APScheduler `BackgroundScheduler`. The scheduler is started via `start_scheduler(app)`, which is called from `create_app()` when `TESTING` is not set. Jobs run in threads that push a Flask application context before touching the database.

| Job ID | Trigger Interval | Function Called | Tables Written | Update Strategy |
|---|---|---|---|---|
| `poll_schedule` | Every 5 minutes | `refresh_schedule()` in `services/slate.py` | `team`, `live_game` | Upsert (`db.session.get()` + `add()`) |
| `poll_scores` | Every 30 seconds | `refresh_scores()` in `services/scores.py` | `live_game` | Update live fields only |
| `poll_odds` | Every 5 minutes | `refresh_odds()` in `services/slate.py` | `odds_snapshot` | Insert-only (append) |
| `compute_fair` | Every 5 minutes | `compute_all_fair()` in `services/implied.py` | `model_fair` | Upsert |
| `prune` | Every 1 hour | `prune_old_snapshots()` in `services/slate.py` | `odds_snapshot` | Delete (age-based purge) |
| `refresh_boxscores` | Every 60 seconds | `refresh_boxscores()` in `services/boxscore.py` | `boxscore` | Upsert by `game_id` |
| `refresh_dashboard_games` | Every 60 seconds | `refresh_dashboard_games()` in `services/dashboard_game.py` | `dashboard_game` | Upsert by `game_id` |
| `refresh_historical` | Daily at 08:00 UTC | `refresh_recent_historical_games()` in `services/historical.py` | `game` | Upsert (30-day window) |
| *(on-demand)* | Manual / startup backfill | `ingest_historical_games()` in `services/historical.py` | `game` | Full upsert by `game_id` |

---

## Job Details

### `poll_schedule` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_schedule()` in `services/slate.py`

**What it does:** Calls `GET /v1/schedule/now` on the NHL API, parses today's game list, and writes every team and game to the database. Uses `db.session.get()` to look up each row by primary key, then `db.session.add()` for new rows — equivalent to an upsert. Re-running the job never creates duplicate rows; it updates in place. Also captures inline odds from the NHL schedule payload as `OddsSnapshot` rows when present.

**Tables read:** none  
**Tables written:** `team` (upsert by `tri_code`), `live_game` (upsert by `game_id`)  
**Update strategy:** Upsert (`db.session.get()` + `db.session.add()`) — safe to run repeatedly

**Staleness signal:** If `live_game.updated_at` is more than ~6 minutes old, this job has likely stalled or the NHL API returned an error.

---

### `poll_scores` — Every 30 Seconds

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_scores()` in `services/scores.py`

**What it does:** Makes a **single call** to `GET /v1/score/now` that covers all of today's games regardless of status — eliminating the N+1 boxscore-per-live-game pattern and the bootstrap gap where newly-started games were missed before the schedule poller ran. Writes `status`, `period`, `clock`, `away_score`, `home_score`, `away_sog`, `home_sog`, and `updated_at` to the `live_game` row for each game found in the response.

**Tables read:** `live_game` (filter by `game_id` from API response)  
**Tables written:** `live_game` (live columns only)  
**Update strategy:** Direct field update — does not upsert or insert new rows

**Staleness signal:** If scores are stale during a live game, verify the `live_game` rows exist (populated by `poll_schedule`).

---

### `poll_odds` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_odds()` in `services/slate.py`

**What it does:** Calls `fetch_odds(game_ids)` from `odds_client.py` to retrieve mock odds for the demo game IDs. A new `OddsSnapshot` row is inserted for each result with the current moneyline odds and a `fetched_at` timestamp. This is an **append-only** job — it never modifies existing rows, which preserves the full odds history for each game.

**Tables read:** none (uses hardcoded demo IDs from `odds_client._MOCK`)  
**Tables written:** `odds_snapshot` (insert only)  
**Update strategy:** Insert-only / append

> **Stub state:** `odds_client.fetch_odds()` returns data from the `_MOCK` dict (deterministic fixture). See `docs/odds-data.md` for the real-API upgrade path.

---

### `compute_fair` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `compute_all_fair()` in `services/implied.py`

**What it does:** For each game, fetches the most recent `OddsSnapshot` row (ordered by `fetched_at DESC`), runs the devig computation, and upserts the result into `model_fair`. Skips games with no snapshot yet.

**Tables read:** `live_game`, `odds_snapshot` (latest per game)  
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

### `prune` — Every 1 Hour

**Source:** `nhl-dashboard/backend/scheduler.py` → `prune_old_snapshots()` in `services/slate.py`

**APScheduler job ID:** `prune`

**What it does:** Deletes all `OddsSnapshot` rows where `fetched_at` is older than 7 days. This prevents unbounded table growth while retaining enough history for short-term odds-movement analysis.

**Tables read:** none  
**Tables written:** `odds_snapshot` (hard delete)  
**Update strategy:** Age-based purge — `DELETE WHERE fetched_at < now() − 7 days`

**Retention policy:** 7-day rolling window, purged hourly.

---

### `refresh_boxscores` — Every 60 Seconds

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_boxscores()` in `services/boxscore.py`

**What it does:** Resolves today's game IDs by querying the `game` table (filtered to `game_date == today`), then calls `GET /v1/gamecenter/{id}/boxscore` for each game. Upserts the result into `boxscore` using `db.session.merge()` on `game_id`. API failures for individual games are logged and skipped so a single bad game does not block the rest.

**Tables read:** `game` (filter by `game_date == today`)  
**Tables written:** `boxscore` (upsert by `game_id`)  
**Update strategy:** Upsert — `db.session.merge()` on `game_id` PK

**Staleness signal:** If `boxscore.updated_at` is stale during a live game, check the `game` table for today's `game_date` entries — if empty, the historical ingest has not run yet.

---

### `refresh_dashboard_games` — Every 60 Seconds

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_dashboard_games()` in `services/dashboard_game.py`

**What it does:** Reads all `Boxscore` records where `game_date == today`, derives a human-readable `status` from `game_state` (`LIVE`/`CRIT` → `live`; `FINAL`/`OFF` → `final`; else → `scheduled`), and upserts each row into `dashboard_game`. Runs on the same 60-second cadence as `refresh_boxscores`.

**Tables read:** `boxscore` (filter by `game_date == today`)  
**Tables written:** `dashboard_game` (upsert by `game_id`)  
**Update strategy:** Upsert — `db.session.merge()` on `game_id` PK

---

### `refresh_historical` — Daily at 08:00 UTC

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_recent_historical_games()` in `services/historical.py`

**What it does:** Fetches all NHL games from `GET https://api.nhle.com/stats/rest/en/game`, filters to the last 30 days, compares each row against the existing `game` table record, and upserts only rows whose fields have changed (or new rows not yet in the DB). Scheduled at 08:00 UTC daily — after overnight games have completed — so final scores are captured the next morning.

**Tables read:** `game` (filter by `game_date >= today − 30 days`)  
**Tables written:** `game` (upsert by `game_id`)  
**Update strategy:** Change-detection upsert — only rows with field changes are updated

**Staleness signal:** Row count in `game` significantly below the API `"total"` field indicates a partial run. Re-run `ingest_historical_games()` manually to complete the backfill.

---

### `ingest_historical_games` — On-Demand Backfill

**Source:** `nhl-dashboard/backend/services/historical.py` → `ingest_historical_games()`

**What it does:** Calls `GET https://api.nhle.com/stats/rest/en/game` (via `get_all_games()` in `nhl_client.py`), iterates over the full `"data"` array, and upserts each row into `game` using `db.session.merge()` on the `game_id` primary key. Safe to re-run at any time — existing rows are updated in place and no duplicates are created.

**Tables read:** none  
**Tables written:** `game` (upsert by `game_id`)  
**Update strategy:** Upsert — `db.session.merge()` on `game_id` PK

**Triggering:** Not registered with APScheduler. Call it manually or from a management script when a full backfill is needed. `refresh_historical` handles the ongoing daily 30-day refresh.

---

### `backfill_boxscores` — On-Demand Backfill

**Source:** `nhl-dashboard/backend/services/boxscore.py` → `backfill_boxscores()`

**What it does:** Fetches and upserts boxscore data for every game in the `game` table (optionally filtered to a single season). Calls `GET /v1/gamecenter/{id}/boxscore` for each game ID, with a 300 ms delay between requests to avoid rate-limiting. Commits in batches of 100. Safe to re-run.

**Tables read:** `game` (all or filtered by `season`)  
**Tables written:** `boxscore` (upsert by `game_id`)  
**Update strategy:** Upsert — `db.session.merge()` on `game_id` PK

**Triggering:** Not registered with APScheduler. Call manually for initial historical boxscore fill.

---

## Local Development Guidance

Not all jobs are equally necessary for local development. The table below indicates which jobs are safe to disable:

| Job ID | Safe to Disable Locally? | Notes |
|---|---|---|
| `poll_schedule` | **No** — required for data | Must run at least once to populate `live_game` and `team` tables |
| `poll_scores` | Yes | No-ops when no live games; disable to reduce noise |
| `poll_odds` | Yes (with stub) | Stub returns fixture data; disable if you don't need odds snapshots |
| `compute_fair` | Yes | Skips gracefully when no snapshots exist |
| `prune` | Yes | No functional impact during short dev sessions |
| `refresh_boxscores` | Yes | Disable if not testing boxscore/dashboard_game flows |
| `refresh_dashboard_games` | Yes | Disable if not testing dashboard_game flow |
| `refresh_historical` | Yes | Cron-daily; not needed for short dev sessions |

To disable a job during development, comment out the corresponding `_scheduler.add_job(...)` call in `scheduler.py:start_scheduler()`. The scheduler itself must still start for the remaining jobs to run.

Alternatively, set `TESTING = True` in the app config — this skips `start_scheduler()` entirely and no background jobs run.

---

## Source Files

| File | Role |
|---|---|
| `nhl-dashboard/backend/scheduler.py` | All job definitions and registration; `start_scheduler(app)` entry point |
| `nhl-dashboard/backend/services/slate.py` | `refresh_schedule()` — schedule fetch and upsert; `refresh_slate()` (legacy, also writes score fields); `refresh_odds()` — odds snapshot insert; `prune_old_snapshots()` — age purge |
| `nhl-dashboard/backend/services/scores.py` | `refresh_scores()` — single-call score + live-update pipeline |
| `nhl-dashboard/backend/services/live.py` | `refresh_live()` (legacy) — per-game boxscore update, superseded by `refresh_scores()` |
| `nhl-dashboard/backend/services/boxscore.py` | `refresh_boxscores()` — live boxscore upsert; `backfill_boxscores()` — historical fill |
| `nhl-dashboard/backend/services/dashboard_game.py` | `refresh_dashboard_games()` — derive app-ready game view from boxscore |
| `nhl-dashboard/backend/services/implied.py` | `devig_two_way()`, `american_to_implied()`, `compute_all_fair()`, `edge()` |
| `nhl-dashboard/backend/odds_client.py` | `fetch_odds(game_ids)` — currently a stub fixture |
| `nhl-dashboard/backend/models.py` | SQLAlchemy models for all tables |
| `nhl-dashboard/backend/services/historical.py` | `ingest_historical_games()` and `refresh_recent_historical_games()` — historical game data |
