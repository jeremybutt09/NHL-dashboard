# Table: `dim_player`

One row per NHL player. Stores biographical data sourced from the roster API — acts as the player reference dimension for fact tables such as `boxscore_skater_stats` and `boxscore_goalie_stats`.

**SQLite database:** `nhl-dashboard/backend/instance/nhl.db`
**Model:** `nhl-dashboard/backend/models.py` → `DimPlayer`

---

## Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `player_id` | `INTEGER` | PRIMARY KEY | NHL player ID — not auto-generated; sourced directly from the roster API `id` field |
| `first_name` | `VARCHAR(64)` | — | Player first name from `firstName.default` |
| `last_name` | `VARCHAR(64)` | — | Player last name from `lastName.default` |
| `sweater_number` | `INTEGER` | — | Jersey number — overwritten on upsert; reflects the most recent season processed |
| `position` | `VARCHAR(2)` | — | Position code: `C`, `L`, `R`, `D`, or `G` |
| `shoots_catches` | `VARCHAR(1)` | — | Handedness: `L` or `R` |
| `height_in_inches` | `INTEGER` | — | Player height in inches |
| `weight_in_pounds` | `INTEGER` | — | Player weight in pounds |
| `birth_date` | `VARCHAR(10)` | — | Date of birth in `YYYY-MM-DD` format |
| `birth_country` | `VARCHAR(3)` | — | Three-letter country code (e.g. `CAN`, `USA`) |
| `headshot_url` | `VARCHAR(255)` | — | CDN URL for the player headshot image |
| `updated_at` | `DATETIME` | — | Eastern timestamp of the last upsert |

---

## Source endpoints

### Roster — `https://api-web.nhle.com/v1/roster/{team}/{season}`

Populates all columns. Called by the backfill notebook (`dim_player_backfill.ipynb`) to seed the full historical roster across all 32 teams and multiple seasons. Rows are upserted by `player_id` so repeated pulls are idempotent; `sweater_number` is overwritten on each upsert to reflect the current season.

| API field | Column | Notes |
|-----------|--------|-------|
| `id` | `player_id` | NHL player ID — primary key |
| `firstName.default` | `first_name` | |
| `lastName.default` | `last_name` | |
| `sweaterNumber` | `sweater_number` | Overwritten on each upsert |
| `positionCode` | `position` | `C`, `L`, `R`, `D`, or `G` |
| `shootsCatches` | `shoots_catches` | `L` or `R` |
| `heightInInches` | `height_in_inches` | |
| `weightInPounds` | `weight_in_pounds` | |
| `birthDate` | `birth_date` | `YYYY-MM-DD` |
| `birthCountry` | `birth_country` | Three-letter country code |
| `headshot` | `headshot_url` | CDN URL |
| *(set at ingest time)* | `updated_at` | Eastern timestamp of the upsert |

---

## Relationships

- `boxscore_skater_stats.player_id` → `dim_player.player_id` (by convention — no FK enforced)
- `boxscore_goalie_stats.player_id` → `dim_player.player_id` (by convention — no FK enforced)
