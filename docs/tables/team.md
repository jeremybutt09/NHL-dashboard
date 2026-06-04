# Table: `team`

One row per NHL franchise. Acts as the central team reference for the dashboard — other tables join to it via `tri_code`.

**SQLite database:** `nhl-dashboard/backend/instance/nhl.db`  
**Model:** `nhl-dashboard/backend/models.py` → `Team`

---

## Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tri_code` | `VARCHAR(3)` | PRIMARY KEY | Three-letter team abbreviation (e.g. `BOS`, `TOR`). Join key for `live_game.away_code` / `live_game.home_code`. |
| `name` | `VARCHAR(64)` | — | Full team display name (e.g. `Boston Bruins`). Populated from the schedule API by concatenating `placeName` + `commonName`. |
| `team_id` | `INTEGER` | UNIQUE, NULLABLE | Numeric team ID from the NHL Stats API. NULL until the stats-API seed job runs. |
| `franchise_id` | `INTEGER` | — | NHL franchise identifier. |
| `full_name` | `VARCHAR(128)` | — | Official full team name from the Stats API (e.g. `Boston Bruins`). |
| `league_id` | `INTEGER` | — | League identifier. NHL = `133`. |
| `raw_tricode` | `VARCHAR(8)` | — | Raw tricode string as returned by the Stats API (may differ from the normalized `tri_code`). |

---

## Source endpoints

### Primary seed — `https://api.nhle.com/stats/rest/en/team`

Populates `team_id`, `franchise_id`, `full_name`, `league_id`, and `raw_tricode`. Called once by the `seed_teams` job in `services/seed.py`.

| API field | Column | Notes |
|-----------|--------|-------|
| `triCode` | `tri_code` | Used as the primary key |
| `id` | `team_id` | Numeric NHL team ID |
| `franchiseId` | `franchise_id` | |
| `fullName` | `full_name` | |
| `leagueId` | `league_id` | |
| `rawTricode` | `raw_tricode` | |

### Schedule upsert — `https://api-web.nhle.com/v1/schedule/now`

Populates `tri_code` and `name` on every schedule poll. One row upserted per unique team appearing in today's games (both away and home sides). Runs every 5 minutes via the `refresh_schedule` job in `services/slate.py`.

| API JSON path | Column | Notes |
|---------------|--------|-------|
| `gameWeek[].games[].awayTeam.abbrev` | `tri_code` | Upsert key |
| `gameWeek[].games[].awayTeam.placeName.default` + `commonName.default` | `name` | Concatenated; falls back to abbreviation |
| `gameWeek[].games[].homeTeam.abbrev` | `tri_code` | Same upsert logic |
| `gameWeek[].games[].homeTeam.placeName.default` + `commonName.default` | `name` | Same as above |

---

## Relationships

- `live_game.away_code` → `team.tri_code`
- `live_game.home_code` → `team.tri_code`
