# Database Schema

The NHL Dashboard uses **SQLite** via **Flask-SQLAlchemy**. The schema is defined in
`nhl-dashboard/backend/models.py` and is initialized at startup with `db.create_all()`.

> **No migration tooling (e.g., Alembic) is in use.** Schema changes require manually
> editing the SQLAlchemy model classes in `models.py` and either dropping/re-creating
> the database or applying `ALTER TABLE` statements by hand.

---

## Tables

### `team`

Stores one row per NHL franchise. The six new columns map directly to fields from the
NHL Stats API (`https://api.nhle.com/stats/rest/en/team`). `team_id` is populated by
the stats-API seeding job (Issue #112) and is NULL until that job runs.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `tri_code` | `String(3)` | `VARCHAR(3)` | **PRIMARY KEY**, NOT NULL | `triCode` | Three-letter team abbreviation (e.g. `BOS`, `TOR`). Join key for `live_game.away_code` / `live_game.home_code` |
| `name` | `String(64)` | `VARCHAR(64)` | — | (schedule API) | Full team display name (e.g. `Boston Bruins`) |
| `team_id` | `Integer` | `INTEGER` | **UNIQUE**, NULLABLE | `id` | Numeric team ID from the NHL Stats API. Unique when non-NULL; NULL until stats-API seed runs |
| `franchise_id` | `Integer` | `INTEGER` | — | `franchiseId` | NHL franchise identifier |
| `full_name` | `String(128)` | `VARCHAR(128)` | — | `fullName` | Official full team name from the Stats API (e.g. `Boston Bruins`) |
| `league_id` | `Integer` | `INTEGER` | — | `leagueId` | League identifier (NHL = 133) |
| `raw_tricode` | `String(8)` | `VARCHAR(8)` | — | `rawTricode` | Raw tricode as returned by the Stats API |

**Indices:** Primary key index on `tri_code`; unique index on `team_id` (NULLs excluded).

---

### `live_game`

Stores today's live-score game rows, sourced from `GET /v1/schedule/now` (metadata) and
`GET /v1/score/now` (live score updates). One row per game; upserted on each poll cycle.
This is the renamed successor of the legacy `game` table (live-scoreboard role).

**Endpoint responsibilities:**

| Field group | Populated by | Endpoint |
|-------------|-------------|---------|
| `game_id`, `away_code`, `home_code`, `start_est`, `game_date`, `venue`, `status` | `refresh_schedule()` | `GET /v1/schedule/now` |
| `away_score`, `home_score`, `period`, `clock`, `away_sog`, `home_sog`, `status` | `refresh_scores()` | `GET /v1/score/now` |

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `live_game.game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | NHL game ID (`gamePk`) from the public NHL API |
| `live_game.start_est` | `DateTime` | `DATETIME` | NOT NULL, **INDEX** | Scheduled puck-drop time in US/Eastern |
| `live_game.game_date` | `String(10)` | `VARCHAR(10)` | — | Calendar date string from API `gameDate` field (e.g. `"2025-01-15"`) |
| `live_game.venue` | `String(120)` | `VARCHAR(120)` | — | Arena name (e.g. `TD Garden`) |
| `live_game.away_code` | `String(3)` | `VARCHAR(3)` | **FOREIGN KEY** → `team.tri_code` | Visiting team abbreviation |
| `live_game.home_code` | `String(3)` | `VARCHAR(3)` | **FOREIGN KEY** → `team.tri_code` | Home team abbreviation |
| `live_game.status` | `String(16)` | `VARCHAR(16)` | NOT NULL | Normalized game state: one of `scheduled`, `live`, `final` |
| `live_game.period` | `String(8)` | `VARCHAR(8)` | NULLABLE | Current period label (e.g. `1st`, `OT`). `NULL` for pre-game |
| `live_game.clock` | `String(8)` | `VARCHAR(8)` | NULLABLE | Time remaining in period (e.g. `12:34`). `NULL` for pre-game |
| `live_game.away_score` | `Integer` | `INTEGER` | DEFAULT 0 | Visiting team's current score |
| `live_game.home_score` | `Integer` | `INTEGER` | DEFAULT 0 | Home team's current score |
| `live_game.away_sog` | `Integer` | `INTEGER` | DEFAULT 0 | Visiting team's shots on goal |
| `live_game.home_sog` | `Integer` | `INTEGER` | DEFAULT 0 | Home team's shots on goal |
| `live_game.updated_at` | `DateTime` | `DATETIME` | — | Eastern timestamp of the most recent write |

**Foreign Keys:**
- `away_code` → `team.tri_code` — links the visiting team to the `team` table.
- `home_code` → `team.tri_code` — links the home team to the `team` table.

**Indices:**
- `ix_live_game_start_est` on `start_est` — used to sort today's slate by puck-drop time.

---

### `odds_snapshot`

Append-only log of money-line odds fetches. One row is inserted per (game, book, fetch)
cycle so that the 24-hour sparkline can be reconstructed from history.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `id` | `Integer` | `INTEGER` | **PRIMARY KEY** (autoincrement), NOT NULL | Surrogate row identifier |
| `game_id` | `Integer` | `INTEGER` | **FOREIGN KEY** → `live_game.game_id`, **INDEX** | The game these odds belong to |
| `fetched_at` | `DateTime` | `DATETIME` | NOT NULL, **INDEX** | Eastern timestamp when odds were recorded |
| `book` | `String(32)` | `VARCHAR(32)` | NOT NULL | Sportsbook identifier (e.g. `consensus`) |
| `away_ml` | `Integer` | `INTEGER` | — | Away team American-format money line (e.g. `+150`) |
| `home_ml` | `Integer` | `INTEGER` | — | Home team American-format money line (e.g. `-170`) |
| `away_implied` | `Float` | `REAL` | — | Away team implied win probability derived from money line |
| `home_implied` | `Float` | `REAL` | — | Home team implied win probability derived from money line |

**Foreign Keys:**
- `game_id` → `live_game.game_id` — ties each odds row to the specific game being priced.

**Indices:**
- `ix_odds_snapshot_game_id` on `game_id` — speeds up lookups for all odds belonging to a game.
- `ix_odds_snapshot_fetched_at` on `fetched_at` — used when slicing odds history by time window for sparkline queries.

---

### `model_fair`

Stores the dashboard's own model-derived fair-value probabilities. One row per game;
updated in place when the model re-computes.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, **FOREIGN KEY** → `live_game.game_id` | The game this fair-value estimate belongs to |
| `away_fair` | `Float` | `REAL` | — | Model's estimated win probability for the away team (0–100) |
| `home_fair` | `Float` | `REAL` | — | Model's estimated win probability for the home team (0–100) |
| `computed_at` | `DateTime` | `DATETIME` | — | Eastern timestamp when the fair-value was last computed |

**Foreign Keys:**
- `game_id` → `live_game.game_id` — the primary key is also a foreign key; this enforces a strict one-to-one relationship between a game and its fair-value estimate.

**Indices:** Primary key index on `game_id`.

---

### `nhl_odds_partner`

Registry of NHL betting partners seeded from the `oddsPartners` array in `GET /v1/score/now`. One row per partner; upserted on every score refresh. Partners are relatively static — they change only when the NHL adds or removes a sportsbook relationship. This table is a prerequisite for `nhl_odds_line`, which holds a foreign key to `nhl_odds_partner.partner_id`.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `partner_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | `partnerId` | NHL's own integer identifier for the betting partner. Used as PK and FK join key for `nhl_odds_line` |
| `country` | `String(2)` | `VARCHAR(2)` | — | `country` | Two-letter country code where this partner is active (e.g. `CA`, `US`) |
| `name` | `String(64)` | `VARCHAR(64)` | NOT NULL | `name` | Display name of the betting partner (e.g. `FanDuel`) |
| `image_url` | `String(255)` | `VARCHAR(255)` | — | `imageUrl` | URL to the partner's logo/image asset hosted on NHL CDN |
| `site_url` | `String(512)` | `VARCHAR(512)` | — | `siteUrl` | Partner's website URL |
| `bg_color` | `String(7)` | `VARCHAR(7)` | — | `bgColor` | Partner's background brand colour as a hex string (e.g. `#0078ff`) |
| `text_color` | `String(7)` | `VARCHAR(7)` | — | `textColor` | Partner's text brand colour as a hex string (e.g. `#FFFFFF`) |
| `accent_color` | `String(7)` | `VARCHAR(7)` | — | `accentColor` | Partner's accent brand colour as a hex string (e.g. `#FFFFFF`) |

**Upsert strategy:** `db.session.merge()` on `partner_id` PK — idempotent and overwrites any changed metadata field on repeated runs.

**Indices:** Primary key index on `partner_id`.

---

### `nhl_odds_line`

Time-series log of per-game, per-partner moneylines sourced from the `awayTeam.odds` and
`homeTeam.odds` arrays in `GET /v1/score/now`. One row is inserted per `(game_id, partner_id)`
per poll cycle, subject to a **3-minute duplicate-suppression window**. Rows are pruned after
**30 days**.

Odds values are stored **as raw strings** — American format (`"-152"`, `"+126"`) for North
American partners and decimal format (`"1.67"`, `"2.24"`) for European partners. Format
detection and normalisation belong in the display/query layer, not at insert time.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `id` | `Integer` | `INTEGER` | **PRIMARY KEY** (autoincrement), NOT NULL | Surrogate row key |
| `game_id` | `Integer` | `INTEGER` | **FOREIGN KEY** → `live_game.game_id`, NOT NULL, **INDEX** | The game these odds belong to |
| `partner_id` | `Integer` | `INTEGER` | **FOREIGN KEY** → `nhl_odds_partner.partner_id`, NOT NULL | The betting partner |
| `fetched_at` | `DateTime` | `DATETIME` | NOT NULL, **INDEX** | Eastern timestamp when this row was recorded |
| `away_value` | `String(16)` | `VARCHAR(16)` | — | Raw odds string for the away team (e.g. `"-152"`, `"1.67"`) |
| `home_value` | `String(16)` | `VARCHAR(16)` | — | Raw odds string for the home team (e.g. `"+126"`, `"2.24"`) |

**Foreign Keys:**
- `game_id` → `live_game.game_id` — ties each odds line to the specific game being priced.
- `partner_id` → `nhl_odds_partner.partner_id` — ties each row to the registered betting partner.

**Indices:**
- `ix_nhl_odds_line_game_id` on `game_id` — efficient lookup of all odds lines for a game.
- `ix_nhl_odds_line_fetched_at` on `fetched_at` — used by the prune job to filter by age.
- `ix_nhl_odds_line_game_partner_fetched` composite on `(game_id, partner_id, fetched_at)` — enables efficient "latest odds per game+partner" queries and the cooldown deduplication check.

**Insert strategy:** pairing by `providerId` — a `{providerId: value}` dict is built for away
and home independently; only providers present in *both* dicts produce a row.

**Pruning:** `prune_nhl_odds_lines()` in `services/slate.py` deletes rows where
`fetched_at < now - 30 days`. Scheduled as a daily job.

---

### `game`

Canonical historical game records from the NHL Stats REST API (Issue #131). Sourced from
`GET https://api.nhle.com/stats/rest/en/game`. One row per game; upserted by
`game_id` so repeated backfill runs are idempotent.

This table is intentionally independent of the `live_game` table — it uses integer team IDs
(not `tri_code` FKs) and covers the full historical game set, not just the current day's slate.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | `id` | NHL numeric game ID — primary key, not auto-generated |
| `eastern_start_time` | `String(16)` | `VARCHAR(16)` | — | `easternStartTime` | Scheduled start time in Eastern time (e.g. `"07:30 PM"`) |
| `game_date` | `String(10)` | `VARCHAR(10)` | **INDEX** | `gameDate` | Game date in `YYYY-MM-DD` format |
| `game_number` | `Integer` | `INTEGER` | — | `gameNumber` | Sequential game number within the season |
| `game_schedule_state_id` | `Integer` | `INTEGER` | — | `gameScheduleStateId` | NHL scheduling state code (e.g. `1` = normal) |
| `game_state_id` | `Integer` | `INTEGER` | — | `gameStateId` | NHL game state code (e.g. `4` = final) |
| `game_type` | `Integer` | `INTEGER` | — | `gameType` | Game type code (e.g. `1` = preseason, `2` = regular season, `3` = playoffs) |
| `home_score` | `Integer` | `INTEGER` | — | `homeScore` | Home team final or current score |
| `home_team_id` | `Integer` | `INTEGER` | — | `homeTeamId` | Numeric ID of the home team (matches `team.team_id` when seeded) |
| `period` | `Integer` | `INTEGER` | — | `period` | Period at which the game ended or is currently in |
| `season` | `Integer` | `INTEGER` | **INDEX** | `season` | Eight-digit season identifier (e.g. `20252026`) |
| `away_score` | `Integer` | `INTEGER` | — | `visitingScore` | Away team final or current score |
| `away_team_id` | `Integer` | `INTEGER` | — | `visitingTeamId` | Numeric ID of the away team |

**Upsert strategy:** `db.session.merge()` on `game_id` PK — idempotent; overwrites changed fields on repeated backfill runs. No pruning: this is a durable historical record.

**Indices:** Primary key index on `game_id`; secondary indices on `game_date` and `season` to support date-range and season-filter queries.

**Source functions:** `ingest_historical_games()` and `refresh_recent_historical_games()` in `nhl-dashboard/backend/services/historical.py`. `refresh_boxscores()` in `services/boxscore.py` reads `game.game_date` to resolve today's game IDs.

---

### `boxscore`

Live boxscore for one NHL game, sourced from `GET /v1/gamecenter/{id}/boxscore`
(Issue #133). One row per game; upserted by `game_id` on each refresh so re-runs are
idempotent. Live fields (score, SOG, period, clock, game_state) are overwritten on
every poll. All timestamps stored in US/Eastern.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | `id` | NHL game ID — not auto-generated |
| `season_id` | `Integer` | `INTEGER` | — | `season` | Eight-digit season identifier |
| `game_type` | `Integer` | `INTEGER` | — | `gameType` | Game type code (2 = regular, 3 = playoffs) |
| `game_date` | `String(10)` | `VARCHAR(10)` | **INDEX** | `gameDate` | Game date in `YYYY-MM-DD` format |
| `venue` | `String(120)` | `VARCHAR(120)` | — | `venue.default` | Arena name |
| `start_time_est` | `DateTime` | `DATETIME` | — | `startTimeUTC` → ET | Puck-drop time converted from UTC to US/Eastern |
| `away_name` | `String(64)` | `VARCHAR(64)` | — | `awayTeam.name.default` | Away team full name |
| `away_abbrev` | `String(8)` | `VARCHAR(8)` | — | `awayTeam.abbrev` | Away team abbreviation |
| `home_name` | `String(64)` | `VARCHAR(64)` | — | `homeTeam.name.default` | Home team full name |
| `home_abbrev` | `String(8)` | `VARCHAR(8)` | — | `homeTeam.abbrev` | Home team abbreviation |
| `away_score` | `Integer` | `INTEGER` | — | `awayTeam.score` | Away team goals |
| `home_score` | `Integer` | `INTEGER` | — | `homeTeam.score` | Home team goals |
| `away_sog` | `Integer` | `INTEGER` | — | `awayTeam.sog` | Away team shots on goal |
| `home_sog` | `Integer` | `INTEGER` | — | `homeTeam.sog` | Home team shots on goal |
| `period` | `String(8)` | `VARCHAR(8)` | — | `periodDescriptor` | Human-readable period label (`1st`, `2nd`, `3rd`, `OT`, `SO`) |
| `clock` | `String(8)` | `VARCHAR(8)` | — | `clock.timeRemaining` | Time remaining in current period |
| `game_state` | `String(8)` | `VARCHAR(8)` | — | `gameState` | NHL game state string (`FUT`, `PRE`, `LIVE`, `CRIT`, `FINAL`, `OFF`) |
| `updated_at` | `DateTime` | `DATETIME` | — | — | Eastern timestamp of last write |

**Upsert strategy:** `db.session.merge()` on `game_id` PK — idempotent.

**Indices:** Primary key index on `game_id`; secondary index on `game_date`.

**Source functions:** `refresh_boxscores()` (scheduled every 60 s) and `backfill_boxscores()` (one-time historical fill) in `nhl-dashboard/backend/services/boxscore.py`.

---

### `dashboard_game`

Today's app-ready game view, derived from the `boxscore` table (Issue #134). One row per
game; only today's games are written. Populated by `refresh_dashboard_games()` on the same
60-second cadence as `refresh_boxscores()`. Designed to serve as the single source for
`GET /api/games/today`.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | NHL gamePk |
| `game_date` | `String(10)` | `VARCHAR(10)` | **INDEX** | Game date in `YYYY-MM-DD` format |
| `venue` | `String(120)` | `VARCHAR(120)` | — | Arena name |
| `start_time_est` | `DateTime` | `DATETIME` | — | Puck-drop time in US/Eastern |
| `away_name` | `String(64)` | `VARCHAR(64)` | — | Away team full name |
| `away_abbrev` | `String(8)` | `VARCHAR(8)` | — | Away team abbreviation |
| `home_name` | `String(64)` | `VARCHAR(64)` | — | Home team full name |
| `home_abbrev` | `String(8)` | `VARCHAR(8)` | — | Home team abbreviation |
| `away_score` | `Integer` | `INTEGER` | — | Away team goals |
| `home_score` | `Integer` | `INTEGER` | — | Home team goals |
| `away_sog` | `Integer` | `INTEGER` | — | Away team shots on goal |
| `home_sog` | `Integer` | `INTEGER` | — | Home team shots on goal |
| `period` | `String(8)` | `VARCHAR(8)` | — | Human-readable period label (`1st`, `2nd`, `3rd`, `OT`, `SO`) |
| `clock` | `String(8)` | `VARCHAR(8)` | — | Time remaining in current period |
| `status` | `String(16)` | `VARCHAR(16)` | — | Derived status: `scheduled`, `live`, or `final` |
| `updated_at` | `DateTime` | `DATETIME` | — | Eastern timestamp of last write |

**Upsert strategy:** `db.session.merge()` on `game_id` PK — overwrites live fields on each refresh.

**Indices:** Primary key index on `game_id`; secondary index on `game_date`.

**Source function:** `refresh_dashboard_games()` in `nhl-dashboard/backend/services/dashboard_game.py`.

---

### `dim_player`

Player biographical dimension sourced from `GET /v1/roster/{team}/{season}`. One row per NHL
player; upserted by `player_id` so repeated roster pulls are idempotent. `sweater_number`
is overwritten on each upsert because it changes between seasons. No FK constraints to other
tables for MVP — `player_id` values correspond to those in `boxscore_skater_stats` /
`boxscore_goalie_stats` by convention, not enforced.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `player_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | `id` | NHL player ID — not auto-generated |
| `first_name` | `String(64)` | `VARCHAR(64)` | — | `firstName.default` | Player's first name |
| `last_name` | `String(64)` | `VARCHAR(64)` | — | `lastName.default` | Player's last name |
| `sweater_number` | `Integer` | `INTEGER` | — | `sweaterNumber` | Jersey number — overwritten on each upsert, changes between seasons |
| `position` | `String(2)` | `VARCHAR(2)` | — | `positionCode` | Position code: `C`, `L`, `R`, `D`, or `G` |
| `shoots_catches` | `String(1)` | `VARCHAR(1)` | — | `shootsCatches` | Shot/catch hand: `L` or `R` |
| `height_in_inches` | `Integer` | `INTEGER` | — | `heightInInches` | Player height in inches |
| `weight_in_pounds` | `Integer` | `INTEGER` | — | `weightInPounds` | Player weight in pounds |
| `birth_date` | `String(10)` | `VARCHAR(10)` | — | `birthDate` | Date of birth in `YYYY-MM-DD` format |
| `birth_country` | `String(3)` | `VARCHAR(3)` | — | `birthCountry` | ISO 3-letter country code (e.g. `CAN`, `USA`) |
| `headshot_url` | `String(255)` | `VARCHAR(255)` | — | `headshot` | CDN URL for the player's headshot image |
| `updated_at` | `DateTime` | `DATETIME` | — | — | Eastern timestamp of last upsert |

**Upsert strategy:** `db.session.merge()` on `player_id` PK — idempotent; overwrites all fields on repeated runs.

**Indices:** Primary key index on `player_id`.

**Source endpoint:** `GET https://api-web.nhle.com/v1/roster/{team}/{season}` — called per team per season. The backfill notebook (Issue #165) iterates all 32 team tricodes.

---

---

### `fact_skater_stats`

Per-game statistics for every forward and defenseman, sourced from
`playerByGameStats.{awayTeam,homeTeam}.{forwards,defense}` in
`GET /v1/gamecenter/{id}/boxscore` (Issue #169). One row per (game_id, player_id);
upserted on each refresh so live-game stats stay current without duplicating rows.
FK'd to `boxscore` (game context) and `dim_player` (biographical data).

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY** (composite), NOT NULL, **FOREIGN KEY** → `boxscore.game_id` | `id` | NHL game identifier |
| `player_id` | `Integer` | `INTEGER` | **PRIMARY KEY** (composite), NOT NULL, **FOREIGN KEY** → `dim_player.player_id` | `playerId` | NHL player identifier |
| `team_id` | `Integer` | `INTEGER` | NOT NULL | `awayTeam.id` / `homeTeam.id` | NHL numeric team ID |
| `side` | `String(4)` | `VARCHAR(4)` | NOT NULL | position in API structure | `'away'` or `'home'` |
| `position_group` | `String(10)` | `VARCHAR(10)` | NOT NULL | position in API structure | `'forwards'` or `'defense'` |
| `position` | `String(2)` | `VARCHAR(2)` | — | `position` | Position code: `C`, `L`, `R`, or `D` |
| `goals` | `Integer` | `INTEGER` | — | `goals` | Goals scored |
| `assists` | `Integer` | `INTEGER` | — | `assists` | Assists |
| `points` | `Integer` | `INTEGER` | — | `points` | Points (goals + assists) |
| `plus_minus` | `Integer` | `INTEGER` | — | `plusMinus` | Plus/minus rating |
| `pim` | `Integer` | `INTEGER` | — | `pim` | Penalty minutes |
| `toi` | `String(8)` | `VARCHAR(8)` | — | `toi` | Time on ice in `MM:SS` format |
| `hits` | `Integer` | `INTEGER` | — | `hits` | Hits delivered |
| `blocked_shots` | `Integer` | `INTEGER` | — | `blockedShots` | Shots blocked |
| `pp_goals` | `Integer` | `INTEGER` | — | `powerPlayGoals` | Power-play goals |
| `pp_points` | `Integer` | `INTEGER` | — | `powerPlayPoints` | Power-play points |
| `sh_goals` | `Integer` | `INTEGER` | — | `shorthandedGoals` | Shorthanded goals |
| `faceoff_win_pct` | `Float` | `REAL` | — | `faceoffWinningPctg` | Faceoff win percentage; NULL for defensemen |
| `giveaways` | `Integer` | `INTEGER` | — | `giveaways` | Giveaways |
| `takeaways` | `Integer` | `INTEGER` | — | `takeaways` | Takeaways |
| `shifts` | `Integer` | `INTEGER` | — | `shifts` | Number of shifts |

**Primary key:** Composite `(game_id, player_id)` — enables `db.session.merge()` for idempotent upserts.

**Foreign Keys:**
- `game_id` → `boxscore.game_id`
- `player_id` → `dim_player.player_id`

**Source function:** `persist_skater_stats()` in `nhl-dashboard/backend/services/player_stats.py`, called by `refresh_boxscore_player_stats()`.

---

### `fact_goalie_stats`

Per-game statistics for every goalie dressed in a game, sourced from
`playerByGameStats.{awayTeam,homeTeam}.goalies` in
`GET /v1/gamecenter/{id}/boxscore` (Issue #169). One row per (game_id, player_id);
upserted on each refresh. The API's `saveShotsAgainst` composite string (`'saves/shots'`)
is parsed into separate `saves` and `shots_against` integer columns.
`decision` is `NULL` for backup goalies who received no decision.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY** (composite), NOT NULL, **FOREIGN KEY** → `boxscore.game_id` | `id` | NHL game identifier |
| `player_id` | `Integer` | `INTEGER` | **PRIMARY KEY** (composite), NOT NULL, **FOREIGN KEY** → `dim_player.player_id` | `playerId` | NHL player identifier |
| `team_id` | `Integer` | `INTEGER` | NOT NULL | `awayTeam.id` / `homeTeam.id` | NHL numeric team ID |
| `side` | `String(4)` | `VARCHAR(4)` | NOT NULL | position in API structure | `'away'` or `'home'` |
| `starter` | `Integer` | `INTEGER` | — | `starter` | `1` = starting goalie, `0` = backup |
| `toi` | `String(8)` | `VARCHAR(8)` | — | `toi` | Time on ice in `MM:SS` format |
| `goals_against` | `Integer` | `INTEGER` | — | `goalsAgainst` | Goals allowed |
| `saves` | `Integer` | `INTEGER` | — | parsed from `saveShotsAgainst` | Saves made (left side of `saves/shots` string) |
| `shots_against` | `Integer` | `INTEGER` | — | parsed from `saveShotsAgainst` | Total shots faced (right side of `saves/shots` string) |
| `save_pct` | `Float` | `REAL` | — | `savePctg` | Save percentage as decimal (0.0–1.0) |
| `es_shots_against` | `Integer` | `INTEGER` | — | `evenStrengthShotsAgainst` | Even-strength shots faced |
| `pp_shots_against` | `Integer` | `INTEGER` | — | `powerPlayShotsAgainst` | Power-play shots faced |
| `sh_shots_against` | `Integer` | `INTEGER` | — | `shorthandedShotsAgainst` | Shorthanded shots faced |
| `pim` | `Integer` | `INTEGER` | — | `pim` | Penalty minutes |
| `decision` | `String(4)` | `VARCHAR(4)` | — | `decision` | Game decision: `W`, `L`, `OTL`, or `NULL` for backup |

**Primary key:** Composite `(game_id, player_id)` — enables `db.session.merge()` for idempotent upserts.

**Foreign Keys:**
- `game_id` → `boxscore.game_id`
- `player_id` → `dim_player.player_id`

**Source function:** `persist_goalie_stats()` in `nhl-dashboard/backend/services/player_stats.py`, called by `refresh_boxscore_player_stats()`.

---

### `fact_boxscore_game_stats`

Canonical game-level boxscore fact table sourced from `GET /v1/gamecenter/{id}/boxscore`
(Issue #170). One row per `game_id`; upserted on each refresh so live fields (score, SOG,
period, clock, game_state) stay current without duplicating rows. Intended as the migration
target for retiring the legacy `boxscore` table in a future issue.

Extends the `boxscore` schema with `away_team_id` and `home_team_id`, which the legacy
table omits. No FK constraints — standalone table, independent of `boxscore`.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Source API field | Description |
|--------|----------------|-------------|-------------|------------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | `id` | NHL game ID — not auto-generated |
| `season_id` | `Integer` | `INTEGER` | — | `season` | Eight-digit season identifier |
| `game_type` | `Integer` | `INTEGER` | — | `gameType` | Game type code (2 = regular, 3 = playoffs) |
| `game_date` | `String(10)` | `VARCHAR(10)` | **INDEX** | `gameDate` | Game date in `YYYY-MM-DD` format |
| `venue` | `String(120)` | `VARCHAR(120)` | — | `venue.default` | Arena name |
| `start_time_est` | `DateTime` | `DATETIME` | — | `startTimeUTC` → ET | Puck-drop time converted from UTC to US/Eastern |
| `game_state` | `String(8)` | `VARCHAR(8)` | — | `gameState` | NHL game state (`FUT`, `PRE`, `LIVE`, `CRIT`, `FINAL`, `OFF`) |
| `away_team_id` | `Integer` | `INTEGER` | — | `awayTeam.id` | Numeric NHL team ID for the away team |
| `away_abbrev` | `String(8)` | `VARCHAR(8)` | — | `awayTeam.abbrev` | Away team abbreviation |
| `away_name` | `String(64)` | `VARCHAR(64)` | — | `awayTeam.name.default` | Away team full name |
| `away_score` | `Integer` | `INTEGER` | — | `awayTeam.score` | Away team goals |
| `away_sog` | `Integer` | `INTEGER` | — | `awayTeam.sog` | Away team shots on goal |
| `home_team_id` | `Integer` | `INTEGER` | — | `homeTeam.id` | Numeric NHL team ID for the home team |
| `home_abbrev` | `String(8)` | `VARCHAR(8)` | — | `homeTeam.abbrev` | Home team abbreviation |
| `home_name` | `String(64)` | `VARCHAR(64)` | — | `homeTeam.name.default` | Home team full name |
| `home_score` | `Integer` | `INTEGER` | — | `homeTeam.score` | Home team goals |
| `home_sog` | `Integer` | `INTEGER` | — | `homeTeam.sog` | Home team shots on goal |
| `clock` | `String(8)` | `VARCHAR(8)` | — | `clock.timeRemaining` | Time remaining in current period |
| `period` | `String(8)` | `VARCHAR(8)` | — | `periodDescriptor` | Human-readable period label (`1st`, `2nd`, `3rd`, `OT`, `SO`) |

**Upsert strategy:** `db.session.merge()` on `game_id` PK — idempotent.

**Indices:** Primary key index on `game_id`; secondary index on `game_date`.

**Key difference from `boxscore`:** Adds `away_team_id` and `home_team_id`. No `updated_at` column. No FK constraints to other tables.

**Source function:** `persist_fact_boxscore_game_stats()` in `nhl-dashboard/backend/services/boxscore.py`, called by `refresh_boxscores()` during the transition period.

---

## Entity-Relationship Summary

```
team (tri_code PK)
  ↑ FK (away_code, home_code)
  live_game (game_id PK) ←── FK (game_id) ── odds_snapshot (id PK)
                        ←── FK (game_id, PK) ── model_fair
                        ←── FK (game_id) ── nhl_odds_line (id PK)

nhl_odds_partner (partner_id PK)
  ↑ FK (partner_id)
  nhl_odds_line (id PK) ──── FK (game_id) ────→ live_game (game_id PK)

game (game_id PK)   ← standalone historical; no FK to live_game or team
  ↓ game_date read by
  boxscore (game_id PK)   ← standalone; no FK to live_game or game
  ↓ derived from
  dashboard_game (game_id PK)   ← standalone; no FK to other tables

dim_player (player_id PK)
  ↑ FK (player_id)            ↑ FK (player_id)
  fact_skater_stats (game_id, player_id composite PK)
    ↑ FK (game_id) → boxscore (game_id PK)
  fact_goalie_stats (game_id, player_id composite PK)
    ↑ FK (game_id) → boxscore (game_id PK)

fact_boxscore_game_stats (game_id PK)   ← standalone; no FK to boxscore or other tables
```

- `live_game` references `team` **twice** (home and away via `tri_code`).
- `odds_snapshot` has a many-to-one relationship with `live_game`: many snapshots per game (one per poll cycle per book).
- `model_fair` has a one-to-one relationship with `live_game`: `game_id` is both the primary key and a foreign key.
- `nhl_odds_line` has a many-to-one relationship with both `live_game` (via `game_id`) and `nhl_odds_partner` (via `partner_id`).
- `game` is a **standalone** historical records table. Its `home_team_id` and `away_team_id` columns hold the same numeric IDs as `team.team_id` but are not enforced via FK constraints.
- `boxscore` is a **standalone** table sourced from `GET /v1/gamecenter/{id}/boxscore`. Its `game_id` values correspond to IDs in the `game` table but there is no FK constraint.
- `dashboard_game` is a **standalone** derived view of today's boxscores. Its rows are copied from `boxscore` by `refresh_dashboard_games()`.
- `fact_skater_stats` and `fact_goalie_stats` reference both `boxscore` (via `game_id`) and `dim_player` (via `player_id`). The composite primary key `(game_id, player_id)` ensures at most one fact row per player per game.
- `fact_boxscore_game_stats` is a **standalone** game-level fact table with no FK constraints. Its `game_id` values correspond to those in `boxscore` but are not enforced. It is the planned migration target for retiring `boxscore`.
