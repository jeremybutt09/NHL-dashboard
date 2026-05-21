# NHL API → Database Field Mappings

This document records exactly which fields from each NHL API response are consumed,
which database column they land in, and any transformation applied. Fields returned
by the API that are **not** consumed by the current implementation are listed in
"Ignored / unused fields" sections at the end of each endpoint.

Source files:
- `nhl-dashboard/backend/nhl_client.py` — `NhlClient.get_schedule_today()`, `NhlClient.get_boxscore()`
- `nhl-dashboard/backend/services/slate.py` — `build_slate()`
- `nhl-dashboard/backend/services/live.py` — `update_live_scores()`
- `nhl-dashboard/backend/odds_client.py` — deterministic fixture stub

---

## Endpoint 1 — `/v1/schedule/now`

**Base URL:** `https://api-web.nhle.com/v1`

Polled by `NhlClient.get_schedule_today()` on the slate poll interval
(`Config.POLL_SLATE_INTERVAL`). The raw JSON is parsed by `_parse_schedule()`,
which filters to `gameWeek[].date == today_utc` before yielding rows.
The normalized list is then persisted by `build_slate()` using `db.session.merge()`
(upsert by primary key).

### → `team` table

One `Team` row is upserted per unique team abbreviation found in today's games
(both away and home).

| API JSON path | `team` column | Transform |
|---|---|---|
| `gameWeek[].games[].awayTeam.abbrev` | `team.code` | None — 3-letter abbreviation used as primary key; existing row is merged, not duplicated |
| `gameWeek[].games[].awayTeam.commonName.default` | `team.name` | None |
| `gameWeek[].games[].homeTeam.abbrev` | `team.code` | None — same merge logic as away team |
| `gameWeek[].games[].homeTeam.commonName.default` | `team.name` | None |

### → `game` table

One `Game` row is upserted per game in today's slate.

| API JSON path | `game` column | Transform |
|---|---|---|
| `gameWeek[].games[].id` | `game.id` | None — integer game ID used as primary key |
| `gameWeek[].games[].startTimeUTC` | `game.start_utc` | ISO 8601 string parsed via `datetime.fromisoformat()` with `Z` → `+00:00` substitution; `tzinfo` stripped before storage (stored as naive UTC `DATETIME`) |
| `gameWeek[].games[].venue.default` | `game.venue` | None |
| `gameWeek[].games[].awayTeam.abbrev` | `game.away_code` | None — FK → `team.code` |
| `gameWeek[].games[].homeTeam.abbrev` | `game.home_code` | None — FK → `team.code` |
| `gameWeek[].games[].gameState` | `game.status` | `_map_game_state()`: `{"LIVE","CRIT"}` → `"live"`, `{"FINAL","OFF"}` → `"final"`, anything else → `"scheduled"` |

**Columns set by `build_slate()` directly (not from API):**

| Column | Value |
|---|---|
| `game.updated_at` | `datetime.now(timezone.utc)` (naive UTC) at the time of the call |

**Columns NOT written by `build_slate()` (left at default / populated by live updater):**

`game.period`, `game.clock`, `game.away_score`, `game.home_score`, `game.away_sog`, `game.home_sog`

### Ignored / unused fields from `/v1/schedule/now`

The following fields are present in the API response but are not consumed by the
current implementation:

| API JSON path | Notes |
|---|---|
| `gameWeek[].games[].season` | Season identifier (e.g. `20252026`) — not stored |
| `gameWeek[].games[].gameType` | Integer type code (e.g. `2` = regular season, `3` = playoffs) — not stored |
| `gameWeek[].games[].gameScheduleState` | Scheduling status string — not stored |
| `gameWeek[].games[].tvBroadcasts[]` | Broadcast network objects — not stored |
| `gameWeek[].games[].awayTeam.score` | Score during a live/final game on the schedule feed — not stored (live updater uses boxscore instead) |
| `gameWeek[].games[].homeTeam.score` | Same as above |
| `gameWeek[].games[].awayTeam.logo` | Team logo CDN URL — not stored in DB (used directly by frontend) |
| `gameWeek[].games[].homeTeam.logo` | Same as above |
| `gameWeek[].games[].periodDescriptor` | Period info available on the schedule feed — ignored in favour of boxscore |
| `gameWeek[].games[].gameCenterLink` | Deep-link path to NHL.com game center — not stored |

---

## Endpoint 2 — `/v1/gamecenter/{game_id}/boxscore`

**Base URL:** `https://api-web.nhle.com/v1`

Polled by `NhlClient.get_boxscore(game_id)` on the live poll interval
(`Config.POLL_LIVE_INTERVAL`). Responses are cached per `game_id` in a 64-slot
`TTLCache`. `update_live_scores()` calls this for every `Game` row whose
`status == "live"` and writes the result back in place.

### → `game` table (live updates only)

| API JSON path | `game` column | Transform |
|---|---|---|
| `gameState` | `game.status` | `_map_game_state()` — same mapping as schedule: `{"LIVE","CRIT"}` → `"live"`, `{"FINAL","OFF"}` → `"final"`, else `"scheduled"` |
| `periodDescriptor` | `game.period` | `_map_period(descriptor)`: `periodType == "OT"` → `"OT"`, `periodType == "SO"` → `"SO"`, `periodType == "REG"` uses `_PERIOD_LABELS` dict (`{1:"1st", 2:"2nd", 3:"3rd"}`); unknown numbers fall back to `str(number)` |
| `clock.timeRemaining` | `game.clock` | None — stored as-is (e.g. `"12:34"`) |
| `awayTeam.score` | `game.away_score` | None — defaults to `0` if key absent |
| `homeTeam.score` | `game.home_score` | None — defaults to `0` if key absent |
| `awayTeam.sog` | `game.away_sog` | None — defaults to `0` if key absent |
| `homeTeam.sog` | `game.home_sog` | None — defaults to `0` if key absent |

**Columns set by `update_live_scores()` directly (not from API):**

| Column | Value |
|---|---|
| `game.updated_at` | `datetime.now(timezone.utc)` (naive UTC) at the time of the call |

### Ignored / unused fields from `/v1/gamecenter/{game_id}/boxscore`

| API JSON path | Notes |
|---|---|
| `id` | Game ID — already known from the DB query; not re-written |
| `season` | Season identifier — not stored |
| `gameType` | Game type integer — not stored |
| `clock.inIntermission` | Boolean intermission flag — not stored |
| `clock.secondsRemaining` | Numeric seconds remaining — not stored (only string form used) |
| `awayTeam.abbrev` | Team abbreviation — already on the `game` row; not re-written |
| `homeTeam.abbrev` | Same as above |
| `awayTeam.name` | Team name object — not stored (already in `team` table) |
| `homeTeam.name` | Same as above |
| `playerByGameStats` | Per-player stats breakdown — not stored |
| `summary` | Goals, penalties, and scratches summaries — not stored |
| `shotsByPeriod` | Period-by-period shot totals — not stored |
| `teamGameStats` | Aggregate team stats (hits, blocks, PIM, etc.) — not stored |

---

## `odds_client.py` — Fixture stub (not a real API)

> **This is NOT a live API integration.** `odds_client.py` contains a hardcoded
> Python list (`_SLATE_ODDS`) of eight odds dictionaries lifted from the
> `Dashboard.html` prototype's `SLATE` constant. It exists so the frontend
> renders realistic-looking data without a real odds provider. All values are
> static and rotate deterministically by `game_id % 8`.

**Function:** `get_odds(game_id: int) -> dict`

Returns one entry from `_SLATE_ODDS` indexed by `game_id % len(_SLATE_ODDS)`.

### Fixture data structure → `odds_snapshot` table

When an odds snapshot is persisted (via the scheduler), the following keys from
the `get_odds()` return value are written to `odds_snapshot`:

| Fixture key | `odds_snapshot` column | Type | Notes |
|---|---|---|---|
| `ml.away` | `odds_snapshot.away_ml` | `Integer` | American-format money line for the away team (e.g. `+120` stored as `120`) |
| `ml.home` | `odds_snapshot.home_ml` | `Integer` | American-format money line for the home team (e.g. `-140` stored as `-140`) |
| `implied.away` | `odds_snapshot.away_implied` | `Float` | Implied win probability for the away team, expressed as a percentage (e.g. `45.0` = 45 %) |
| `implied.home` | `odds_snapshot.home_implied` | `Float` | Implied win probability for the home team (e.g. `55.0` = 55 %) |

### Fixture keys that are available but not currently persisted to the database

| Fixture key | Notes |
|---|---|
| `ml_open.away` / `ml_open.home` | Opening money-line values — present in fixture but no DB column yet |
| `fair.away` / `fair.home` | Model-derived fair probabilities — intended for `model_fair` table but not written by the stub pipeline |
| `edge` | Implied edge (fair minus implied) — computed from the fixture; not persisted |
| `movement_24h` | 24-element array of hourly implied probabilities used for the sparkline — returned by `get_odds()` but not written to `odds_snapshot` |

---

## Transformation Reference

| Function | Location | Input | Output |
|---|---|---|---|
| `_map_game_state(state)` | `nhl_client.py` | Raw `gameState` string from NHL API | `"live"` \| `"final"` \| `"scheduled"` |
| `_map_period(descriptor)` | `nhl_client.py` | `periodDescriptor` dict with `number` and `periodType` keys | `"1st"` \| `"2nd"` \| `"3rd"` \| `"OT"` \| `"SO"` \| `str(n)` |
