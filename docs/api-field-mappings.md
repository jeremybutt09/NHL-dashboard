# NHL API → Database Field Mappings

This document records exactly which fields from each NHL API response are consumed,
which database column they land in, and any transformation applied. Fields returned
by the API that are **not** consumed by the current implementation are listed in
"Ignored / unused fields" sections at the end of each endpoint.

Source files:
- `nhl-dashboard/backend/nhl_client.py` — `get_schedule_now()`, `get_score_now()`, `get_boxscore()` (module-level functions, no class)
- `nhl-dashboard/backend/services/slate.py` — `refresh_slate()`
- `nhl-dashboard/backend/services/scores.py` — `refresh_scores()` (primary score + live-update pipeline)
- `nhl-dashboard/backend/services/live.py` — `refresh_live()`, `_update_from_boxscore()` (superseded; see legacy note under Endpoint 2)
- `nhl-dashboard/backend/odds_client.py` — deterministic fixture stub

---

## Endpoint 1 — `/v1/schedule/now`

**Base URL:** `https://api-web.nhle.com/v1`

Polled by `get_schedule_now()` on the slate poll interval
(`Config.POLL_SLATE_INTERVAL`). The raw JSON is parsed by `refresh_slate()` in
`services/slate.py`, which filters to the `gameWeek` block whose `date` matches
today's UTC date before yielding rows. The normalized list is then persisted using
`db.session.get()` + `db.session.add()` (upsert by primary key).

### → `team` table

One `Team` row is upserted per unique team abbreviation found in today's games
(both away and home).

| API JSON path | `team` column | Transform |
|---|---|---|
| `gameWeek[].games[].awayTeam.abbrev` | `team.tri_code` | None — 3-letter abbreviation used as primary key; existing row is updated, not duplicated |
| `gameWeek[].games[].awayTeam.placeName.default` + `commonName.default` | `team.name` | Concatenated to form full name (e.g. `Toronto Maple Leafs`); falls back to abbreviation |
| `gameWeek[].games[].homeTeam.abbrev` | `team.tri_code` | None — same upsert logic as away team |
| `gameWeek[].games[].homeTeam.placeName.default` + `commonName.default` | `team.name` | Same as above |

### → `game` table

One `Game` row is upserted per game in today's slate.

| API JSON path | `game` column | Transform |
|---|---|---|
| `gameWeek[].games[].id` | `game.id` | None — integer game ID used as primary key |
| `gameWeek[].games[].startTimeUTC` | `game.start_est` | ISO 8601 string parsed via `datetime.fromisoformat()`, then converted to `US/Eastern` via `zoneinfo`; stored as Eastern `DATETIME` |
| `gameWeek[].games[].gameDate` | `game.game_date` | Stored verbatim as a `VARCHAR(10)` string (e.g. `"2025-01-15"`) — not derived from `start_est` |
| `gameWeek[].games[].venue.default` | `game.venue` | None |
| `gameWeek[].games[].awayTeam.abbrev` | `game.away_code` | None — FK → `team.tri_code` |
| `gameWeek[].games[].homeTeam.abbrev` | `game.home_code` | None — FK → `team.tri_code` |
| `gameWeek[].games[].gameState` | `game.status` | Inline in `refresh_slate()`: `{"LIVE","CRIT"}` → `"live"`, `{"FINAL","OFF"}` → `"final"`, anything else → `"scheduled"` |
| `gameWeek[].games[].awayTeam.score` | `game.away_score` | Defaults to `0` if key absent |
| `gameWeek[].games[].homeTeam.score` | `game.home_score` | Defaults to `0` if key absent |

**Columns set by `refresh_slate()` directly (not from API):**

| Column | Value |
|---|---|
| `game.updated_at` | `datetime.now(timezone.utc)` (naive UTC) at the time of the call |

**Columns NOT written by `refresh_slate()` (left at default / populated by live updater):**

`game.period`, `game.clock`, `game.away_sog`, `game.home_sog`

### Ignored / unused fields from `/v1/schedule/now`

The following fields are present in the API response but are not consumed by the
current implementation:

| API JSON path | Notes |
|---|---|
| `gameWeek[].games[].season` | Season identifier (e.g. `20252026`) — not stored |
| `gameWeek[].games[].gameType` | Integer type code (e.g. `2` = regular season, `3` = playoffs) — not stored |
| `gameWeek[].games[].gameScheduleState` | Scheduling status string — not stored |
| `gameWeek[].games[].tvBroadcasts[]` | Broadcast network objects — not stored |
| `gameWeek[].games[].awayTeam.logo` | Team logo CDN URL — not stored in DB (used directly by frontend) |
| `gameWeek[].games[].homeTeam.logo` | Same as above |
| `gameWeek[].games[].periodDescriptor` | Period info available on the schedule feed — ignored in favour of boxscore |
| `gameWeek[].games[].gameCenterLink` | Deep-link path to NHL.com game center — not stored |

---

## Endpoint 2 — `/v1/score/now`

**Base URL:** `https://api-web.nhle.com/v1`

Polled by `get_score_now()` on the score poll interval (`Config.POLL_SCORES_INTERVAL`).
Responses are cached in a 128-slot `TTLCache` with a 5-minute TTL. `refresh_scores()`
in `services/scores.py` makes a **single call** that covers all of today's games
regardless of status — eliminating the N+1 boxscore-per-live-game pattern and the
bootstrap gap where newly-started games were missed before the slate poller ran.

### → `game` table (status + live updates)

| API JSON path | `game` column | Transform |
|---|---|---|
| `games[].gameState` | `game.status` | `_map_game_state()` (`services/scores.py`): `{"FINAL","OFF"}` → `"final"`, `{"LIVE","CRIT"}` → `"live"`, else → `"scheduled"` |
| `games[].periodDescriptor` | `game.period` | `_parse_period()` (`services/scores.py`): `periodType == "OT"` → `"OT"`, `"SO"` → `"SO"`, `"REG"` uses ordinal dict `{1:"1st", 2:"2nd", 3:"3rd"}`; unknown numbers fall back to `f'{n}th'` |
| `games[].clock.timeRemaining` | `game.clock` | None — stored as-is (e.g. `"12:34"`) |
| `games[].awayTeam.score` | `game.away_score` | Falls back to current DB value if key absent |
| `games[].homeTeam.score` | `game.home_score` | Falls back to current DB value if key absent |
| `games[].awayTeam.sog` | `game.away_sog` | Falls back to current DB value if key absent |
| `games[].homeTeam.sog` | `game.home_sog` | Falls back to current DB value if key absent |

**Columns set by `refresh_scores()` directly (not from API):**

| Column | Value |
|---|---|
| `game.updated_at` | `datetime.now(timezone.utc)` (naive UTC) at the time of the call |

### Ignored / unused fields from `/v1/score/now`

The following fields are present in the API response but are not consumed by `refresh_scores()`:

| API JSON path | Notes |
|---|---|
| `games[].clock.secondsRemaining` | Numeric seconds remaining — not stored (only string form used) |
| `games[].clock.running` | Boolean running flag — not stored |
| `games[].clock.inIntermission` | Boolean intermission flag — not stored |
| `games[].period` | Top-level integer period count (distinct from `periodDescriptor`) — not stored |
| `games[].periodDescriptor.maxRegulationPeriods` | Max regulation periods (usually 3) — not stored |
| `games[].gameOutcome.lastPeriodType` | Final period type string — not stored |
| `games[].goals[]` | Per-goal details array — not stored |
| `games[].seriesStatus` | Playoff series status object — not stored |
| `games[].tvBroadcasts[]` | Broadcast network objects — not stored |
| `games[].neutralSite` | Boolean neutral-site flag — not stored |
| `games[].venueTimezone` | Venue timezone string — not stored |
| `games[].threeMinRecap` | Recap video URL — not stored |
| `games[].condensedGame` | Condensed game video URL — not stored |
| `games[].gameCenterLink` | Deep-link path to NHL.com game center — not stored |
| `games[].seriesUrl` | Playoff series URL — not stored |
| `games[].threeMinRecapFr` | French-language recap URL — not stored |
| `games[].condensedGameFr` | French-language condensed game URL — not stored |

### Legacy endpoint — `/v1/gamecenter/{game_id}/boxscore`

> **Superseded by `/v1/score/now`.** The original live-update implementation
> (`refresh_live()` / `_update_from_boxscore()` in `services/live.py`) polled
> `get_boxscore(game_id)` for every `Game` row with `status == "live"`. This
> per-game approach was replaced by the single-call `refresh_scores()` strategy
> above, which also handles games that have just started and are not yet marked
> live in the database.

---

## `odds_client.py` — Fixture stub (not a real API)

> **This is NOT a live API integration.** `odds_client.py` contains a hardcoded
> Python dict (`_MOCK`) of eight odds entries keyed by game ID (1001–1008). It
> exists so the frontend renders realistic-looking data without a real odds
> provider. All values are static.

**Function:** `fetch_odds(game_ids: list[int]) -> list[dict]`

Takes a list of game IDs and returns a list of odds dicts — one per matching entry
in `_MOCK`. Game IDs not found in `_MOCK` are silently skipped.

### Return shape → `odds_snapshot` table

When an odds snapshot is persisted (via `refresh_odds()` in the scheduler), the
following keys from each `fetch_odds()` dict are written to `odds_snapshot`:

| Return key | `odds_snapshot` column | Type | Notes |
|---|---|---|---|
| `game_id` | `odds_snapshot.game_id` | `Integer` | FK to `game.id` |
| `book` | `odds_snapshot.book` | `String(32)` | Always `'consensus'` in stub |
| `away_ml` | `odds_snapshot.away_ml` | `Integer` | American-format money line for the away team (e.g. `+120` stored as `120`) |
| `home_ml` | `odds_snapshot.home_ml` | `Integer` | American-format money line for the home team (e.g. `-140` stored as `-140`) |
| `away_ml_open` | not persisted | `Integer` | Opening money-line — present in `_MOCK` but no DB column in `odds_snapshot` |
| `home_ml_open` | not persisted | `Integer` | Same as above |

> `away_implied` and `home_implied` stored in `odds_snapshot` are **computed** from
> `away_ml` / `home_ml` by calling `american_to_implied()` inside `refresh_odds()`.
> They are not returned by `fetch_odds()` — they are derived locally before insertion.

---

## Endpoint 3 — `https://api.nhle.com/stats/rest/en/game`

**Base URL:** `https://api.nhle.com/stats/rest/en`

Called once (or on-demand) by `get_all_games()` in `nhl_client.py`. The full
historical game list is returned in a single response under the `"data"` key.
Parsed and persisted by `ingest_historical_games()` in `services/historical.py`
using `db.session.get()` + `db.session.add()` on `game_id` (idempotent upsert).

### → `nhl_historical_game` table

One row per game; all fields mapped directly with no transformation.

| API JSON path | `nhl_historical_game` column | Notes |
|---|---|---|
| `data[].id` | `game_id` | Integer primary key — not auto-generated |
| `data[].easternStartTime` | `eastern_start_time` | String as returned (e.g. `"07:30 PM"`) |
| `data[].gameDate` | `game_date` | String in `YYYY-MM-DD` format |
| `data[].gameNumber` | `game_number` | Integer |
| `data[].gameScheduleStateId` | `game_schedule_state_id` | Integer state code |
| `data[].gameStateId` | `game_state_id` | Integer state code |
| `data[].gameType` | `game_type` | Integer (2 = regular season, 3 = playoffs) |
| `data[].homeScore` | `home_score` | Integer |
| `data[].homeTeamId` | `home_team_id` | Integer; matches `team.team_id` when seeded |
| `data[].period` | `period` | Integer period at game end or current period |
| `data[].season` | `season` | Integer, e.g. `20252026` |
| `data[].visitingScore` | `visiting_score` | Integer |
| `data[].visitingTeamId` | `visiting_team_id` | Integer; matches `team.team_id` when seeded |

### Ignored / unused fields from the Stats REST `/game` endpoint

| API JSON path | Notes |
|---|---|
| `total` | Total row count from the API pagination envelope — not stored |

---

## Transformation Reference

Status-mapping and period-mapping logic live in named helpers in `services/scores.py`
and also inline in the older `services/slate.py` and `services/live.py`:

| Operation | Source location | Input → Output |
|---|---|---|
| Game state → status string | `_map_game_state()` (`services/scores.py`) | `{"FINAL","OFF"}` → `"final"`, `{"LIVE","CRIT"}` → `"live"`, else → `"scheduled"` |
| Game state → status string | Inline in `refresh_slate()` (`services/slate.py`) | Same mapping; applied during schedule ingestion |
| Game state → status string | Inline in `_update_from_boxscore()` (`services/live.py`) | Same mapping; applied to boxscore `gameState` (legacy) |
| `periodDescriptor` → period label | `_parse_period()` (`services/scores.py`) | `"OT"` / `"SO"` / `"1st"` / `"2nd"` / `"3rd"` / `f'{n}th'` |
| `periodDescriptor` → period label | Inline in `_update_from_boxscore()` (`services/live.py`) | Same logic (legacy) |
