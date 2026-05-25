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
| `game_id`, `away_code`, `home_code`, `start_utc`, `venue`, `status` | `refresh_schedule()` | `GET /v1/schedule/now` |
| `away_score`, `home_score`, `period`, `clock`, `away_sog`, `home_sog` | score poller (#117) | `GET /v1/score/now` |

`refresh_schedule()` runs every `POLL_SCHEDULE_INTERVAL` seconds (default: 300 s) and immediately at startup. It seeds game rows so the score poller has rows to update. Score fields are intentionally left at their default (0) by the schedule job.

| Column | SQLAlchemy Type | SQLite Type | Constraints | Description |
|--------|----------------|-------------|-------------|-------------|
| `game_id` | `Integer` | `INTEGER` | **PRIMARY KEY**, NOT NULL | NHL game ID (`gamePk`) from the public NHL API |
| `start_utc` | `DateTime` | `DATETIME` | NOT NULL, **INDEX** | Scheduled puck-drop time in UTC |
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
- `ix_game_start_utc` on `start_utc` — used by the games route to filter and sort today's slate efficiently.

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

## Entity-Relationship Summary

```
team (tri_code PK)
  ↑ FK (away_code)
  game (game_id PK) ←── FK (game_id) ── odds_snapshot (id PK)
  ↑ FK (home_code)
  team (tri_code PK)  game (game_id PK) ←── FK (game_id, PK) ── model_fair

nhl_odds_partner (partner_id PK)   [no FK to game; referenced by nhl_odds_line #119]
```

- Each `game` references `team` **twice** (home and away). Both foreign keys point at `team.tri_code`.
- `odds_snapshot` has a many-to-one relationship with `game`: many snapshots can exist per game (one per poll cycle per book).
- `model_fair` has a one-to-one relationship with `game`: `game_id` is both the primary key and a foreign key, preventing duplicate fair-value rows for the same game.
- `nhl_odds_partner` is a standalone reference table with no foreign keys of its own. It will be referenced by `nhl_odds_line` (Issue #119) via `partner_id`.
