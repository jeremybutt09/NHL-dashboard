# NHL API → Database Field Mappings

This document records exactly which fields from each NHL API response are consumed,
which database column they land in, and any transformation applied. Fields returned
by the API that are **not** consumed by the current implementation are listed in
"Ignored / unused fields" sections at the end of each endpoint.

Source files:
- `nhl-dashboard/backend/nhl_client.py` — `get_schedule_now()`, `get_boxscore()` (module-level functions, no class)
- `nhl-dashboard/backend/services/slate.py` — `refresh_slate()`
- `nhl-dashboard/backend/services/live.py` — `refresh_live()`, `_update_from_boxscore()`
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
| `gameWeek[].games[].awayTeam.abbrev` | `team.code` | None — 3-letter abbreviation used as primary key; existing row is updated, not duplicated |
| `gameWeek[].games[].awayTeam.placeName.default` + `commonName.default` | `team.name` | Concatenated to form full name (e.g. `Toronto Maple Leafs`); falls back to abbreviation |
| `gameWeek[].games[].homeTeam.abbrev` | `team.code` | None — same upsert logic as away team |
| `gameWeek[].games[].homeTeam.placeName.default` + `commonName.default` | `team.name` | Same as above |

### → `game` table

One `Game` row is upserted per game in today's slate.

| API JSON path | `game` column | Transform |
|---|---|---|
| `gameWeek[].games[].id` | `game.id` | None — integer game ID used as primary key |
| `gameWeek[].games[].startTimeUTC` | `game.start_utc` | ISO 8601 string parsed via `datetime.fromisoformat()` with `Z` → `+00:00` substitution; `tzinfo` stripped before storage (stored as naive UTC `DATETIME`) |
| `gameWeek[].games[].venue.default` | `game.venue` | None |
| `gameWeek[].games[].awayTeam.abbrev` | `game.away_code` | None — FK → `team.code` |
| `gameWeek[].games[].homeTeam.abbrev` | `game.home_code` | None — FK → `team.code` |
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

## Endpoint 2 — `/v1/gamecenter/{game_id}/boxscore`

**Base URL:** `https://api-web.nhle.com/v1`

Polled by `get_boxscore(game_id)` on the live poll interval
(`Config.POLL_LIVE_INTERVAL`). Responses are cached per URL path string (e.g.
`/gamecenter/12345/boxscore`) in a 128-slot `TTLCache` with a 5-minute TTL.
`refresh_live()` calls this for every `Game` row whose `status == "live"` and
passes the result to `_update_from_boxscore()` which writes the data back in place.

### → `game` table (live updates only)

| API JSON path | `game` column | Transform |
|---|---|---|
| `gameState` | `game.status` | Inline in `_update_from_boxscore()` (live.py): `{"LIVE","CRIT"}` → `"live"`, `{"FINAL","OFF"}` → `"final"`, else unchanged |
| `periodDescriptor` | `game.period` | Inline in `_update_from_boxscore()` (live.py): `periodType == "OT"` → `"OT"`, `periodType == "SO"` → `"SO"`, `periodType == "REG"` uses ordinal dict `{1:"1st", 2:"2nd", 3:"3rd"}`; unknown numbers fall back to `f'{n}th'` |
| `clock.timeRemaining` | `game.clock` | None — stored as-is (e.g. `"12:34"`) |
| `awayTeam.score` | `game.away_score` | Defaults to current value if key absent |
| `homeTeam.score` | `game.home_score` | Defaults to current value if key absent |
| `awayTeam.sog` | `game.away_sog` | Defaults to current value if key absent |
| `homeTeam.sog` | `game.home_sog` | Defaults to current value if key absent |

**Columns set by `refresh_live()` / `_update_from_boxscore()` directly (not from API):**

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

## Transformation Reference

Status-mapping and period-mapping logic are implemented **inline** — there are no
named helper functions in `nhl_client.py`. The logic lives in two places:

| Operation | Source location | Input → Output |
|---|---|---|
| Game state → status string | Inline in `refresh_slate()` (`services/slate.py`) | `{"LIVE","CRIT"}` → `"live"`, `{"FINAL","OFF"}` → `"final"`, else → `"scheduled"` |
| Game state → status string | Inline in `_update_from_boxscore()` (`services/live.py`) | Same mapping; applied to boxscore `gameState` |
| `periodDescriptor` → period label | Inline in `_update_from_boxscore()` (`services/live.py`) | `"OT"` / `"SO"` / `"1st"` / `"2nd"` / `"3rd"` / `f'{n}th'` |
