# Data Pipeline: Background Jobs, Poll Intervals, and Data Flow

This document describes all background jobs that drive data writes to the NHL Dashboard database, their polling intervals, the tables they touch, and the end-to-end data flow from NHL API call to API response. Use it as the first stop when debugging data freshness or staleness issues.

---

## End-to-End Data Flow

```
NHL /v1/roster/{team}/{season}  [one call per team, 32 teams total]
  └──> backfill_dim_player()  ──> dim_player (upsert by player_id)

NHL /v1/score/now
  └──> refresh_nhl_odds()  ──> nhl_odds_partner (upsert), nhl_odds_line (insert)

NHL /v1/gamecenter/{id}/boxscore
  └──> refresh_boxscores()
         └──> boxscore (upsert by game_id)
         └──> fact_boxscore_game_stats (upsert by game_id) [Issue #170]
  └──> refresh_boxscore_player_stats()
         └──> persist_skater_stats()  ──> fact_skater_stats (upsert by game_id, player_id)
         └──> persist_goalie_stats()  ──> fact_goalie_stats (upsert by game_id, player_id)

NHL /v1/player/{player_id}/landing   [on-demand — called when a player_id is missing from dim_player]
  └──> _ensure_dim_player()  ──> dim_player (upsert by player_id)

boxscore (today's rows)
  └──> refresh_dashboard_games() ──> dashboard_game (upsert by game_id)

fetch_odds() [stub fixture]
  └──> refresh_odds()
         └──> _poll_odds() ──> odds_snapshot (insert-only / append)

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
| `poll_nhl_odds` | Every 30 seconds | `refresh_nhl_odds()` in `services/scores.py` | `nhl_odds_partner`, `nhl_odds_line` | Upsert partners; insert odds lines |
| `poll_odds` | Every 5 minutes | `refresh_odds()` in `services/slate.py` | `odds_snapshot` | Insert-only (append) |
| `prune` | Every 1 hour | `prune_old_snapshots()` in `services/slate.py` | `odds_snapshot` | Delete (age-based purge) |
| `refresh_boxscores` | Every 60 seconds | `refresh_boxscores()` in `services/boxscore.py` | `boxscore`, `fact_boxscore_game_stats` | Upsert by `game_id` |
| `prune_stale_boxscores` | Every 60 seconds | `prune_stale_boxscores()` in `services/boxscore.py` | `boxscore`, `game` | Delete stale rows |
| `refresh_player_stats` | Every 60 seconds | `refresh_boxscore_player_stats()` in `services/player_stats.py` | `fact_skater_stats`, `fact_goalie_stats`, `dim_player` | Upsert by `(game_id, player_id)`; backfills `dim_player` for unknown players |
| `refresh_dashboard_games` | Every 60 seconds | `refresh_dashboard_games()` in `services/dashboard_game.py` | `dashboard_game` | Upsert by `game_id` |
| `refresh_historical` | Daily at 08:00 UTC | `refresh_recent_historical_games()` in `services/historical.py` | `game` | Upsert (30-day window) |
| *(on-demand)* | Manual / startup backfill | `ingest_historical_games()` in `services/historical.py` | `game` | Full upsert by `game_id` |
| *(on-demand)* | Manual / notebook-driven | `backfill_dim_player()` (Issue #165 notebook) | `dim_player` | Upsert by `player_id` |

---

## Job Details

### `poll_schedule` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_schedule()` in `services/slate.py`

**What it does:** Calls `GET /v1/schedule/now` on the NHL API, parses today's game list, and writes every team and game to the database. Uses `db.session.get()` to look up each row by primary key, then `db.session.add()` for new rows — equivalent to an upsert. Re-running the job never creates duplicate rows; it updates in place. Also captures inline odds from the NHL schedule payload as `OddsSnapshot` rows when present.

### `poll_nhl_odds` — Every 30 Seconds

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_nhl_odds()` in `services/scores.py`

**What it does:** Makes a single call to `GET /v1/score/now`, upserts the `oddsPartners` registry into `nhl_odds_partner`, then inserts `nhl_odds_line` rows for each game's partner odds. A 3-minute duplicate-suppression window (`_ODDS_COOLDOWN_SECONDS`) prevents duplicate rows within the same poll cycle.

**Tables read:** `nhl_odds_line` (cooldown check per game/partner)  
**Tables written:** `nhl_odds_partner` (upsert via `db.session.merge()`), `nhl_odds_line` (insert — `away_value`, `home_value`, `fetched_at`)  
**Update strategy:** Partners — upsert; odds lines — insert-only with cooldown deduplication

---

### `poll_odds` — Every 5 Minutes

**Source:** `nhl-dashboard/backend/scheduler.py` → `refresh_odds()` in `services/slate.py`

**What it does:** Calls `fetch_odds(game_ids)` from `odds_client.py` to retrieve mock odds for the demo game IDs. A new `OddsSnapshot` row is inserted for each result with the current moneyline odds and a `fetched_at` timestamp. This is an **append-only** job — it never modifies existing rows, which preserves the full odds history for each game.

**Tables read:** none (uses hardcoded demo IDs from `odds_client._MOCK`)  
**Tables written:** `odds_snapshot` (insert only)  
**Update strategy:** Insert-only / append

> **Stub state:** `odds_client.fetch_odds()` returns data from the `_MOCK` dict (deterministic fixture). See `docs/odds-data.md` for the real-API upgrade path.

#### Devig Formula (used in API response)

The raw implied probabilities derived from `odds_snapshot` (e.g. `away_implied = 52.4`, `home_implied = 50.0`) sum to more than 100 because the sportsbook embeds a vig (margin). The devig step removes the vig so the two probabilities sum to exactly 100, yielding fair-value win probabilities.

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

The resulting `away_fair` and `home_fair` values sum to 100 and are returned directly in the `/api/games/today` response.

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
**Tables written:** `boxscore` (upsert by `game_id`), `fact_boxscore_game_stats` (upsert by `game_id`)  
**Update strategy:** Upsert — `db.session.merge()` on `game_id` PK for both tables

During the transition period (Issues #170 → retirement of `boxscore`), `refresh_boxscores()` writes
both `boxscore` and `fact_boxscore_game_stats` in the same pass. `fact_boxscore_game_stats` adds
`away_team_id` and `home_team_id` absent from `boxscore`.

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

### `backfill_dim_player` — On-Demand Roster Backfill

**Source:** `nhl-dashboard/notebooks/` (Issue #165 backfill notebook)

**What it does:** Iterates all 32 NHL team tricodes, calls `GET /v1/roster/{team}/{season}`
for each team with the current season string, and upserts the player records into
`dim_player` using `db.session.merge()` on `player_id`. Players who appear on multiple
rosters (trades, waivers) are upserted in place — no duplicates. `sweater_number` and
other mutable fields are overwritten on each run so the table stays current.

**Tables read:** none  
**Tables written:** `dim_player` (upsert by `player_id`)  
**Update strategy:** Upsert — `db.session.merge()` on `player_id` PK

**Triggering:** Not a scheduled APScheduler job. Run the backfill notebook (Issue #165) once
per season or whenever roster data needs refreshing. No scheduler registration is required
for the MVP.

**`dim_player` role:** Provides the biographical anchor for future fact tables
(`boxscore_skater_stats`, `boxscore_goalie_stats`). `player_id` values in those fact tables
correspond to `dim_player.player_id` by convention; FK constraints are not enforced for MVP.

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
| `poll_nhl_odds` | Yes | Disable to avoid external API calls during local development |
| `poll_odds` | Yes (with stub) | Stub returns fixture data; disable if you don't need odds snapshots |
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
| `nhl-dashboard/backend/services/slate.py` | `refresh_odds()` — odds snapshot insert; `prune_old_snapshots()` — age purge; `build_today_response()` — serve /api/games/today |
| `nhl-dashboard/backend/services/scores.py` | `refresh_nhl_odds()` — poll /v1/score/now and write nhl_odds_line rows |
| `nhl-dashboard/backend/services/boxscore.py` | `refresh_boxscores()` — live boxscore upsert; `backfill_boxscores()` — historical fill; `persist_fact_boxscore_game_stats()` — game-level fact table upsert |
| `nhl-dashboard/backend/services/dashboard_game.py` | `refresh_dashboard_games()` — derive app-ready game view from boxscore |
| `nhl-dashboard/backend/services/implied.py` | `devig_two_way()`, `american_to_implied()`, `edge()` — pure probability math |
| `nhl-dashboard/backend/odds_client.py` | `fetch_odds(game_ids)` — currently a stub fixture |
| `nhl-dashboard/backend/models.py` | SQLAlchemy models for all tables |
| `nhl-dashboard/backend/services/historical.py` | `ingest_historical_games()` and `refresh_recent_historical_games()` — historical game data |
| `nhl-dashboard/notebooks/` (Issue #165) | `backfill_dim_player()` — roster backfill for `dim_player` |
