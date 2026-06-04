# NHL API → Database Field Mappings

This document records exactly which fields from each NHL API response are consumed,
which database column they land in, and any transformation applied. Fields returned
by the API that are **not** consumed by the current implementation are listed in
"Ignored / unused fields" sections at the end of each endpoint.

Source files:
- `nhl-dashboard/backend/nhl_client.py` — `get_schedule_now()`, `get_score_now()`, `get_boxscore()`, `get_player_landing()` (module-level functions, no class)
- `nhl-dashboard/backend/services/scores.py` — `refresh_nhl_odds()` (partner odds pipeline via `/v1/score/now`)
- `nhl-dashboard/backend/services/boxscore.py` — `refresh_boxscores()`, `backfill_boxscores()`
- `nhl-dashboard/backend/services/player_stats.py` — `persist_skater_stats()`, `persist_goalie_stats()`, `refresh_boxscore_player_stats()`
- `nhl-dashboard/backend/odds_client.py` — deterministic fixture stub

---

## Endpoint 1 — `/v1/schedule/now`

**Base URL:** `https://api-web.nhle.com/v1`

Polled by `get_schedule_now()`. Inline odds from the schedule payload are captured as `OddsSnapshot` rows via `refresh_odds()` in `services/slate.py`. This endpoint is no longer used to seed game rows.

### → `team` table

One `Team` row is upserted per unique team abbreviation found in today's games (both away and home) when a new team is encountered.

| API JSON path | `team` column | Transform |
|---|---|---|
| `gameWeek[].games[].awayTeam.abbrev` | `team.tri_code` | None — 3-letter abbreviation used as primary key |
| `gameWeek[].games[].awayTeam.placeName.default` + `commonName.default` | `team.name` | Concatenated to form full name |
| `gameWeek[].games[].homeTeam.abbrev` | `team.tri_code` | Same as above |
| `gameWeek[].games[].homeTeam.placeName.default` + `commonName.default` | `team.name` | Same as above |

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

Polled by `get_score_now()` on the score poll interval (`Config.POLL_SCORE_INTERVAL`).
Responses are cached in a 128-slot `TTLCache` with a 5-minute TTL. `refresh_nhl_odds()`
in `services/scores.py` makes a **single call** that covers all of today's games,
upserts the partner registry, and inserts odds lines for each game.

### → `nhl_odds_partner` table

One row upserted per entry in the `oddsPartners` array.

| API JSON path | `nhl_odds_partner` column | Transform |
|---|---|---|
| `oddsPartners[].partnerId` | `nhl_odds_partner.partner_id` | None — integer PK |
| `oddsPartners[].name` | `nhl_odds_partner.name` | None |
| `oddsPartners[].country` | `nhl_odds_partner.country` | None |
| `oddsPartners[].imageUrl` | `nhl_odds_partner.image_url` | None |
| `oddsPartners[].siteUrl` | `nhl_odds_partner.site_url` | None |

### → `nhl_odds_line` table

One row inserted per (game, partner) pair per poll cycle, subject to 3-minute cooldown.

| API JSON path | `nhl_odds_line` column | Transform |
|---|---|---|
| `games[].id` | `nhl_odds_line.game_id` | None — integer game ID |
| `games[].awayTeam.odds[].providerId` | `nhl_odds_line.partner_id` | Paired with matching home providerId; unknown partnerIds skipped |
| `games[].awayTeam.odds[].value` | `nhl_odds_line.away_value` | Stored verbatim as string (e.g. `"-152"`, `"1.67"`) |
| `games[].homeTeam.odds[].value` | `nhl_odds_line.home_value` | Stored verbatim as string |

### Ignored / unused fields from `/v1/score/now`

The following fields are present in the API response but are not consumed by `refresh_nhl_odds()`:

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

---

## Endpoint 3 — `/v1/gamecenter/{game_id}/boxscore`

**Base URL:** `https://api-web.nhle.com/v1`

Called by `get_boxscore(game_id)` in `nhl_client.py`. Polled by `refresh_boxscores()`
in `services/boxscore.py` every 60 seconds (`Config.POLL_BOXSCORE_INTERVAL`) for all
games on today's slate. Also used by `backfill_boxscores()` for historical fills.
All timestamps are converted from UTC to US/Eastern at ingest time.

### → `boxscore` table

One row per game; upserted by `game_id` on each call.

| API JSON path | `boxscore` column | Transform |
|---|---|---|
| `id` | `boxscore.game_id` | Integer primary key — not auto-generated |
| `season` | `boxscore.season_id` | Integer (e.g. `20252026`) |
| `gameType` | `boxscore.game_type` | Integer (2 = regular, 3 = playoffs) |
| `gameDate` | `boxscore.game_date` | String in `YYYY-MM-DD` format |
| `venue.default` | `boxscore.venue` | String extracted from `venue` dict; falls back to empty string |
| `startTimeUTC` | `boxscore.start_time_est` | Parsed via `fromisoformat()`, converted to `US/Eastern` |
| `awayTeam.name.default` | `boxscore.away_name` | Extracted from name dict; falls back to empty string |
| `awayTeam.abbrev` | `boxscore.away_abbrev` | None |
| `homeTeam.name.default` | `boxscore.home_name` | Extracted from name dict; falls back to empty string |
| `homeTeam.abbrev` | `boxscore.home_abbrev` | None |
| `awayTeam.score` | `boxscore.away_score` | None |
| `homeTeam.score` | `boxscore.home_score` | None |
| `awayTeam.sog` | `boxscore.away_sog` | None |
| `homeTeam.sog` | `boxscore.home_sog` | None |
| `periodDescriptor` | `boxscore.period` | `_parse_period()` in `services/boxscore.py`: `"OT"` / `"SO"` / ordinal |
| `clock.timeRemaining` | `boxscore.clock` | None — stored as-is |
| `gameState` | `boxscore.game_state` | None — stored verbatim (`FUT`, `PRE`, `LIVE`, `CRIT`, `FINAL`, `OFF`) |

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
| `game_id` | `odds_snapshot.game_id` | `Integer` | NHL game ID (no FK constraint) |
| `book` | `odds_snapshot.book` | `String(32)` | Always `'consensus'` in stub |
| `away_ml` | `odds_snapshot.away_ml` | `Integer` | American-format money line for the away team (e.g. `+120` stored as `120`) |
| `home_ml` | `odds_snapshot.home_ml` | `Integer` | American-format money line for the home team (e.g. `-140` stored as `-140`) |
| `away_ml_open` | not persisted | `Integer` | Opening money-line — present in `_MOCK` but no DB column in `odds_snapshot` |
| `home_ml_open` | not persisted | `Integer` | Same as above |

> `away_implied` and `home_implied` stored in `odds_snapshot` are **computed** from
> `away_ml` / `home_ml` by calling `american_to_implied()` inside `refresh_odds()`.
> They are not returned by `fetch_odds()` — they are derived locally before insertion.

---

## Endpoint 4 — `https://api.nhle.com/stats/rest/en/game`

**Base URL:** `https://api.nhle.com/stats/rest/en`

Called once (or on-demand) by `get_all_games()` in `nhl_client.py`. The full
historical game list is returned in a single response under the `"data"` key.
Parsed and persisted by `ingest_historical_games()` or `refresh_recent_historical_games()`
in `services/historical.py` using `db.session.merge()` on `game_id` (idempotent upsert).

### → `game` table

One row per game; all fields mapped directly with no transformation. This table was
updated to `game` table name in Issue #131.

| API JSON path | `game` column | Notes |
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
| `data[].visitingScore` | `away_score` | Integer |
| `data[].visitingTeamId` | `away_team_id` | Integer; matches `team.team_id` when seeded |

### Ignored / unused fields from the Stats REST `/game` endpoint

| API JSON path | Notes |
|---|---|
| `total` | Total row count from the API pagination envelope — not stored |

---

## Endpoint 5 — `/v1/roster/{team}/{season}`

**Base URL:** `https://api-web.nhle.com/v1`

Called once per team per season when populating `dim_player`. The backfill notebook
(Issue #165) iterates all 32 NHL team tricodes and the current season string
(e.g. `20252026`). Parsed and persisted using `db.session.merge()` on `player_id`
(idempotent upsert).

### → `dim_player` table

One row per player; all fields sourced from the `forwards`, `defensemen`, and `goalies`
arrays in the response. All three arrays share the same per-player object shape.

| API JSON path | `dim_player` column | Transform |
|---|---|---|
| `forwards[].id` / `defensemen[].id` / `goalies[].id` | `player_id` | Integer primary key — not auto-generated |
| `forwards[].firstName.default` | `first_name` | Extracted from nested `default` key |
| `forwards[].lastName.default` | `last_name` | Extracted from nested `default` key |
| `forwards[].sweaterNumber` | `sweater_number` | Integer; overwritten on each upsert |
| `forwards[].positionCode` | `position` | String, e.g. `C`, `L`, `R`, `D`, `G` |
| `forwards[].shootsCatches` | `shoots_catches` | `L` or `R` |
| `forwards[].heightInInches` | `height_in_inches` | Integer |
| `forwards[].weightInPounds` | `weight_in_pounds` | Integer |
| `forwards[].birthDate` | `birth_date` | String in `YYYY-MM-DD` format |
| `forwards[].birthCountry` | `birth_country` | ISO 3-letter code (e.g. `CAN`, `USA`) |
| `forwards[].headshot` | `headshot_url` | CDN URL string |
| *(computed at persist time)* | `updated_at` | Eastern timestamp set by the persist function |

The same field paths apply to `defensemen[]` and `goalies[]` — all three arrays are
iterated in a single pass when backfilling.

### Ignored / unused fields from `/v1/roster/{team}/{season}`

| API JSON path | Notes |
|---|---|
| `forwards[].lastName.cs` / `.fr` etc. | Localized name variants — only `default` is stored |
| `forwards[].firstName.cs` / `.fr` etc. | Same as above |
| `forwards[].headshots[]` | Alternative headshot sizes — only the top-level `headshot` URL is stored |
| `forwards[].heroImage` | Large promotional image URL — not stored |
| `forwards[].birthCity.default` | Birth city — not stored in MVP |
| `forwards[].birthStateProvince.default` | Birth state/province — not stored in MVP |
| `forwards[].spokenLanguages[]` | Languages spoken — not stored |

---

## Endpoint 6 — `/v1/gamecenter/{game_id}/boxscore` → `fact_skater_stats` and `fact_goalie_stats`

**Base URL:** `https://api-web.nhle.com/v1`

The same `get_boxscore()` call that populates the `boxscore` table also feeds player
stats into `fact_skater_stats` and `fact_goalie_stats` via `persist_skater_stats()` and
`persist_goalie_stats()` in `services/player_stats.py` (Issue #169).

### → `fact_skater_stats` table

One row per `(game_id, player_id)` for every entry in `playerByGameStats.*.forwards` and
`playerByGameStats.*.defense`.

| API JSON path | `fact_skater_stats` column | Transform |
|---|---|---|
| `id` | `game_id` | Integer composite PK component |
| `awayTeam.id` / `homeTeam.id` | `team_id` | Integer — the team the player is on |
| *(structural position)* | `side` | `'away'` or `'home'` derived from position in `playerByGameStats` |
| *(structural position)* | `position_group` | `'forwards'` or `'defense'` derived from array key |
| `playerByGameStats.*.*.playerId` | `player_id` | Integer composite PK component |
| `playerByGameStats.*.*.position` | `position` | `C` / `L` / `R` / `D` |
| `playerByGameStats.*.*.goals` | `goals` | Integer |
| `playerByGameStats.*.*.assists` | `assists` | Integer |
| `playerByGameStats.*.*.points` | `points` | Integer |
| `playerByGameStats.*.*.plusMinus` | `plus_minus` | Integer |
| `playerByGameStats.*.*.pim` | `pim` | Integer (penalty minutes) |
| `playerByGameStats.*.*.toi` | `toi` | `MM:SS` string — stored verbatim |
| `playerByGameStats.*.*.hits` | `hits` | Integer |
| `playerByGameStats.*.*.blockedShots` | `blocked_shots` | Integer |
| `playerByGameStats.*.*.powerPlayGoals` | `pp_goals` | Integer |
| `playerByGameStats.*.*.powerPlayPoints` | `pp_points` | Integer |
| `playerByGameStats.*.*.shorthandedGoals` | `sh_goals` | Integer |
| `playerByGameStats.*.*.faceoffWinningPctg` | `faceoff_win_pct` | Float; NULL for defensemen |
| `playerByGameStats.*.*.giveaways` | `giveaways` | Integer |
| `playerByGameStats.*.*.takeaways` | `takeaways` | Integer |
| `playerByGameStats.*.*.shifts` | `shifts` | Integer |

### → `fact_goalie_stats` table

One row per `(game_id, player_id)` for every entry in `playerByGameStats.*.goalies`.

| API JSON path | `fact_goalie_stats` column | Transform |
|---|---|---|
| `id` | `game_id` | Integer composite PK component |
| `awayTeam.id` / `homeTeam.id` | `team_id` | Integer |
| *(structural position)* | `side` | `'away'` or `'home'` |
| `playerByGameStats.*.goalies[].playerId` | `player_id` | Integer composite PK component |
| `playerByGameStats.*.goalies[].starter` | `starter` | Integer: `1` = starter, `0` = backup |
| `playerByGameStats.*.goalies[].toi` | `toi` | `MM:SS` string — stored verbatim |
| `playerByGameStats.*.goalies[].goalsAgainst` | `goals_against` | Integer |
| `playerByGameStats.*.goalies[].saveShotsAgainst` | `saves` | Left side of `'saves/shots'` string split on `'/'`, cast to int |
| `playerByGameStats.*.goalies[].saveShotsAgainst` | `shots_against` | Right side of `'saves/shots'` string split on `'/'`, cast to int |
| `playerByGameStats.*.goalies[].savePctg` | `save_pct` | Float 0.0–1.0 |
| `playerByGameStats.*.goalies[].evenStrengthShotsAgainst` | `es_shots_against` | Integer |
| `playerByGameStats.*.goalies[].powerPlayShotsAgainst` | `pp_shots_against` | Integer |
| `playerByGameStats.*.goalies[].shorthandedShotsAgainst` | `sh_shots_against` | Integer |
| `playerByGameStats.*.goalies[].pim` | `pim` | Integer |
| `playerByGameStats.*.goalies[].decision` | `decision` | `W`, `L`, `OTL`, or `None` when key absent (backup) |

---

## Endpoint 7 — `/v1/player/{player_id}/landing`

**Base URL:** `https://api-web.nhle.com/v1`

Called by `get_player_landing(player_id)` in `nhl_client.py` when a player appears in
`fact_skater_stats` or `fact_goalie_stats` but has no row in `dim_player`. The
`_ensure_dim_player()` function in `services/player_stats.py` calls this endpoint to
backfill biographical data before writing the fact row.

### → `dim_player` table

| API JSON path | `dim_player` column | Transform |
|---|---|---|
| `playerId` | `player_id` | Integer primary key — not auto-generated |
| `firstName.default` | `first_name` | Extracted from nested `default` key |
| `lastName.default` | `last_name` | Extracted from nested `default` key |
| `sweaterNumber` | `sweater_number` | Integer; overwritten on each upsert |
| `position` | `position` | String: `C`, `L`, `R`, `D`, or `G` |
| `shootsCatches` | `shoots_catches` | `L` or `R` |
| `heightInInches` | `height_in_inches` | Integer |
| `weightInPounds` | `weight_in_pounds` | Integer |
| `birthDate` | `birth_date` | String in `YYYY-MM-DD` format |
| `birthCountry` | `birth_country` | ISO 3-letter country code |
| `headshot` | `headshot_url` | CDN URL string |
| *(computed at persist time)* | `updated_at` | Eastern timestamp set by `_ensure_dim_player()` |

---

## Transformation Reference

Status-mapping and period-mapping logic live in named helpers in `services/scores.py`
and also inline in the older `services/slate.py` and `services/live.py`:

| Operation | Source location | Input → Output |
|---|---|---|
| Game state → status string | `_map_game_state()` (`services/scores.py`) | `{"FINAL","OFF"}` → `"final"`, `{"LIVE","CRIT"}` → `"live"`, else → `"scheduled"` |
| Game state → status string | Inline in `refresh_schedule()` (`services/slate.py`) | Same mapping; applied during schedule ingestion |
| Game state → status string | Inline in `_update_from_boxscore()` (`services/live.py`) | Same mapping; applied to boxscore `gameState` (legacy) |
| `periodDescriptor` → period label | `_parse_period()` (`services/scores.py`) | `"OT"` / `"SO"` / `"1st"` / `"2nd"` / `"3rd"` / `f'{n}th'` |
| `periodDescriptor` → period label | `_parse_period()` (`services/boxscore.py`) | Same logic; used by boxscore ingest |
| `gameState` → status string | Inline in `_build_from_boxscores()` (`services/slate.py`) | `{"LIVE","CRIT"}` → `"live"`, `{"FINAL","OFF"}` → `"final"`, else → `"scheduled"` |
| `startTimeUTC` → Eastern datetime | `_build_boxscore()` (`services/boxscore.py`) | UTC ISO 8601 → `US/Eastern` datetime via `zoneinfo` |
