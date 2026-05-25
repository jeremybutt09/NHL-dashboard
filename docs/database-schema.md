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
| `tri_code` | `String(3)` | `VARCHAR(3)` | **PRIMARY KEY**, NOT NULL | `triCode` | Three-letter team abbreviation (e.g. `BOS`, `TOR`). Join key for `game.away_code` / `game.home_code` |
| `name` | `String(64)` | `VARCHAR(64)` | — | (schedule API) | Full team display name (e.g. `Boston Bruins`) |
| `team_id` | `Integer` | `INTEGER` | **UNIQUE**, NULLABLE | `id` | Numeric team ID from the NHL Stats API. Unique when non-NULL; NULL until stats-API seed runs |
| `franchise_id` | `Integer` | `INTEGER` | — | `franchiseId` | NHL franchise identifier |
| `full_name` | `String(128)` | `VARCHAR(128)` | — | `fullName` | Official full team name from the Stats API (e.g. `Boston Bruins`) |
| `league_id` | `Integer` | `INTEGER` | — | `leagueId` | League identifier (NHL = 133) |
| `raw_tricode` | `String(8)` | `VARCHAR(8)` | — | `rawTricode` | Raw tricode as returned by the Stats API |

**Indices:** Primary key index on `tri_code`; unique index on `team_id` (NULLs excluded).

---

### `game`

Stores one row per NHL game. Updated in place during each poll cycle.

**Endpoint responsibilities** (Issue #116):

| Field group | Populated by | Endpoint |
|-------------|-------------|---------|
| `game_id`, `away_code`, `home_code`, `start_est`, `game_date`, `venue`, `status` | `refresh_schedule()` | `GET /v1/schedule/now` |
| `away_score`, `home_score`, `period`, `clock`, `away_sog`, `home_sog` | score poller (#117) | `GET /v1/score/now` |

`refresh_schedule()` runs every `POLL_SCHEDULE_INTERVAL` seconds (default: 300 s) and immediately at startup. It seeds game rows so the score poller has rows to update. Score fields are intentionally left at their default (0) by the schedule job.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | NHL game ID (`gamePk`) from the public NHL API |
| `start_est` | `DateTime` | `DATETIME` | NOT NULL, **INDEX** | Scheduled puck-drop time in US/Eastern |
| `game_date` | `String(10)` | `VARCHAR(10)` | — | Calendar date string from API `gameDate` field (e.g. `"2025-01-15"`) |
| `venue` | `String(120)` | `VARCHAR(120)` | — | Arena name (e.g. `TD Garden`) |
| `away_code` | `String(3)` | `VARCHAR(3)` | **FOREIGN KEY** → `team.tri_code` | Visiting team abbreviation |
| `home_code` | `String(3)` | `VARCHAR(3)` | **FOREIGN KEY** → `team.tri_code` | Home team abbreviation |
| `status` | `String(16)` | `VARCHAR(16)` | NOT NULL | Normalized game state: one of `scheduled`, `live`, `final` |
| `period` | `String(8)` | `VARCHAR(8)` | NULLABLE | Current period label (e.g. `1st`, `OT`). `NULL` for pre-game |
| `clock` | `String(8)` | `VARCHAR(8)` | NULLABLE | Time remaining in period (e.g. `12:34`). `NULL` for pre-game |
| `away_score` | `Integer` | `INTEGER` | DEFAULT 0 | Visiting team's current score |
| `home_score` | `Integer` | `INTEGER` | DEFAULT 0 | Home team's current score |
| `away_sog` | `Integer` | `INTEGER` | DEFAULT 0 | Visiting team's shots on goal |
| `home_sog` | `Integer` | `INTEGER` | DEFAULT 0 | Home team's shots on goal |
| `updated_at` | `DateTime` | `DATETIME` | — | Timestamp of the most recent write from the poll job |

**Foreign Keys:**
- `away_code` → `team.tri_code` — links the visiting team to the `team` table.
- `home_code` → `team.tri_code` — links the home team to the `team` table.

**Indices:**
- `ix_game_start_est` on `start_est` — used by the games route to sort today's slate by puck-drop time.

---

### `odds_snapshot`

Append-only log of money-line odds fetches. One row is inserted per (game, book, fetch)
cycle so that the 24-hour sparkline can be reconstructed from history.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `id` | `Integer` | `INTEGER` | **PRIMARY KEY** (autoincrement), NOT NULL | Surrogate row identifier |
| `game_id` | `Integer` | `INTEGER` | **FOREIGN KEY** → `game.game_id`, **INDEX** | The game these odds belong to |
| `fetched_at` | `DateTime` | `DATETIME` | NOT NULL, **INDEX** | UTC timestamp when odds were recorded |
| `book` | `String(32)` | `VARCHAR(32)` | NOT NULL | Sportsbook identifier (e.g. `stub`) |
| `away_ml` | `Integer` | `INTEGER` | — | Away team American-format money line (e.g. `+150`) |
| `home_ml` | `Integer` | `INTEGER` | — | Home team American-format money line (e.g. `-170`) |
| `away_implied` | `Float` | `REAL` | — | Away team implied win probability derived from money line |
| `home_implied` | `Float` | `REAL` | — | Home team implied win probability derived from money line |

**Foreign Keys:**
- `game_id` → `game.game_id` — ties each odds row to the specific game being priced.

**Indices:**
- `ix_odds_snapshot_game_id` on `game_id` — speeds up lookups for all odds belonging to a game (FK → `game.game_id`).
- `ix_odds_snapshot_fetched_at` on `fetched_at` — used when slicing odds history by time window for sparkline queries.

---

### `model_fair`

Stores the dashboard's own model-derived fair-value probabilities. One row per game;
updated in place when the model re-computes.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, **FOREIGN KEY** → `game.game_id` | The game this fair-value estimate belongs to |
| `away_fair` | `Float` | `REAL` | — | Model's estimated win probability for the away team (0–1) |
| `home_fair` | `Float` | `REAL` | — | Model's estimated win probability for the home team (0–1) |
| `computed_at` | `DateTime` | `DATETIME` | — | UTC timestamp when the fair-value was last computed |

**Foreign Keys:**
- `game_id` → `game.game_id` — the primary key is also a foreign key; this enforces a strict one-to-one relationship between a game and its fair-value estimate.

**Indices:** Primary key index on `game_id`.

---

### `nhl_odds_partner`

Registry of NHL betting partners seeded from the `oddsPartners` array in `GET /v1/score/now`. One row per partner; upserted on every score refresh. Partners are relatively static — they change only when the NHL adds or removes a sportsbook relationship. This table is a prerequisite for `nhl_odds_line` (Issue #119), which holds a foreign key to `nhl_odds_partner.partner_id`.

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

**Upsert strategy:** `db.session.merge()` on `partner_id` PK — idempotent and overwrites any changed metadata field on repeated runs. No pruning: partner rows are reference data, not time-series.

**Indices:** Primary key index on `partner_id`.

---

### `nhl_odds_line`

Time-series log of per-game, per-partner moneylines sourced from the `awayTeam.odds` and
`homeTeam.odds` arrays in `GET /v1/score/now`. One row is inserted per `(game_id, partner_id)`
per poll cycle, subject to a **3-minute duplicate-suppression window** (mirrors `odds_snapshot`
behaviour). Rows are pruned after **30 days** (longer than `odds_snapshot`'s 7 days, since
cross-partner history is more analytically valuable).

Odds values are stored **as raw strings** — American format (`"-152"`, `"+126"`) for North
American partners and decimal format (`"1.67"`, `"2.24"`) for European partners. Format
detection and normalisation belong in the display/query layer, not at insert time.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `id` | `Integer` | `INTEGER` | **PRIMARY KEY** (autoincrement), NOT NULL | Surrogate row key |
| `game_id` | `Integer` | `INTEGER` | **FOREIGN KEY** → `game.game_id`, NOT NULL, **INDEX** | The game these odds belong to |
| `partner_id` | `Integer` | `INTEGER` | **FOREIGN KEY** → `nhl_odds_partner.partner_id`, NOT NULL | The betting partner |
| `fetched_at` | `DateTime` | `DATETIME` | NOT NULL, **INDEX** | UTC timestamp when this row was recorded |
| `away_value` | `String(16)` | `VARCHAR(16)` | — | Raw odds string for the away team (e.g. `"-152"`, `"1.67"`) |
| `home_value` | `String(16)` | `VARCHAR(16)` | — | Raw odds string for the home team (e.g. `"+126"`, `"2.24"`) |

**Foreign Keys:**
- `game_id` → `game.game_id` — ties each odds line to the specific game being priced.
- `partner_id` → `nhl_odds_partner.partner_id` — ties each row to the registered betting partner.

**Indices:**
- `ix_nhl_odds_line_game_id` on `game_id` — efficient lookup of all odds lines for a game.
- `ix_nhl_odds_line_fetched_at` on `fetched_at` — used by the prune job to filter by age.
- `ix_nhl_odds_line_game_partner_fetched` composite on `(game_id, partner_id, fetched_at)` — enables efficient "latest odds per game+partner" queries and the cooldown deduplication check.

**Insert strategy:** pairing by `providerId` — a `{providerId: value}` dict is built for away
and home independently; only providers present in *both* dicts produce a row. Unknown
`providerId` values (not in `nhl_odds_partner`) are skipped with a `WARNING` log.

**Pruning:** `prune_nhl_odds_lines()` in `services/slate.py` deletes rows where
`fetched_at < now - 30 days`. Should be run as a scheduled job (daily is sufficient).

---

### `nhl_historical_game`

Complete historical game records backfilled from the NHL Stats REST API
(`GET https://api.nhle.com/stats/rest/en/game`). One row per game; upserted by
`game_id` on each backfill run. This table is intentionally independent of the
`game` table — it uses integer team IDs (not `tri_code` FKs) and covers the full
historical game set, not just the current day's slate.

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
| `visiting_score` | `Integer` | `INTEGER` | — | `visitingScore` | Visiting (away) team final or current score |
| `visiting_team_id` | `Integer` | `INTEGER` | — | `visitingTeamId` | Numeric ID of the visiting (away) team |

**Upsert strategy:** `db.session.merge()` on `game_id` PK — idempotent; overwrites changed fields on repeated backfill runs. No pruning: this is a durable historical record.

**Indices:** Primary key index on `game_id`; secondary indices on `game_date` and `season` to support date-range and season-filter queries.

**Source function:** `ingest_historical_games()` in `nhl-dashboard/backend/services/historical.py`.

---

## Entity-Relationship Summary

```
team (tri_code PK)
  ↑ FK (away_code)
  game (game_id PK) ←── FK (game_id) ── odds_snapshot (id PK)
  ↑ FK (home_code)
  team (tri_code PK)  game (game_id PK) ←── FK (game_id, PK) ── model_fair

nhl_odds_partner (partner_id PK)
  ↑ FK (partner_id)
  nhl_odds_line (id PK) ──── FK (game_id) ────→ game (game_id PK)

nhl_historical_game (game_id PK)   ← standalone; no FK to game or team
```

- Each `game` references `team` **twice** (home and away). Both foreign keys point at `team.tri_code`.
- `odds_snapshot` has a many-to-one relationship with `game`: many snapshots can exist per game (one per poll cycle per book).
- `model_fair` has a one-to-one relationship with `game`: `game_id` is both the primary key and a foreign key, preventing duplicate fair-value rows for the same game.
- `nhl_odds_partner` is a reference table. It is referenced by `nhl_odds_line` via `partner_id`.
- `nhl_odds_line` has a many-to-one relationship with both `game` (via `game_id`) and `nhl_odds_partner` (via `partner_id`). Many lines can exist per game+partner pair (one per poll window).
- `nhl_historical_game` is a **standalone** table with no foreign keys. Its `home_team_id` and `visiting_team_id` columns hold the same numeric IDs as `team.team_id` but are not enforced via FK constraints, keeping the historical backfill independent of the live-slate data model.
