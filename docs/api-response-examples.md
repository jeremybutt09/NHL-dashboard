# API Response Examples

Annotated JSON response shapes for every NHL Dashboard backend endpoint.
These examples are derived from the mock SLATE fixture in
`nhl-dashboard/backend/services/slate.py` and the route tests under
`nhl-dashboard/tests/`.  All field names are **stable contract** — do not
rename without updating both the backend and this document.

---

## GET /api/health

Returns the health status of the API server and its database connection.

### Success response — HTTP 200

```json
{
  "status": "ok",
  "db": "connected",
  "last_poll": "2026-05-17T01:23:45Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"ok"` when the server is healthy. `"error"` when the DB is unreachable. |
| `db` | `string` | `"connected"` when SQLite is reachable; `"error"` otherwise. |
| `last_poll` | `string \| null` | ISO 8601 UTC timestamp of the most recent scheduler poll, or `null` if no poll has run yet. |

### Error response — HTTP 500

Returned when the database is unreachable.

```json
{
  "status": "error",
  "db": "error",
  "last_poll": null
}
```

---

## GET /api/games/today

Returns the full game slate for today, including live score data, moneyline
odds, implied probabilities, fair-value model output, and a 24-hour odds
movement sparkline.

### Top-level envelope

```json
{
  "updated_at": "2026-05-17T01:30:00Z",
  "games": [ ... ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `updated_at` | `string` | ISO 8601 UTC timestamp of when this response was assembled. |
| `games` | `array` | Ordered list of game objects for today, sorted by `start` time ascending. Empty array `[]` when no games are scheduled. |

---

### Game object — live game example

A game in `"live"` status includes a populated `live` block with real-time
score and period information.

```json
{
  "id": 1001,
  "away": {
    "code": "TOR",
    "name": "Toronto Maple Leafs",
    "record": "24-18-4",
    "l10": "6-3-1"
  },
  "home": {
    "code": "BOS",
    "name": "Boston Bruins",
    "record": "30-15-6",
    "l10": "7-2-1"
  },
  "start": "2026-05-17T00:00:00Z",
  "venue": "TD Garden",
  "status": "live",
  "live": {
    "period": "2nd",
    "clock": "12:34",
    "away_score": 3,
    "home_score": 2,
    "away_sog": 18,
    "home_sog": 22
  },
  "ml": { "away": 120, "home": -140 },
  "ml_open": { "away": 115, "home": -135 },
  "implied": { "away": 45.0, "home": 55.0 },
  "fair": { "away": 47.5, "home": 52.5 },
  "edge": 2.1,
  "movement_24h": [46.38, 44.95, 44.14, 45.07, 44.14, 43.78, 44.91, 44.44,
                   44.9,  45.95, 47.13, 46.81, 45.87, 45.58, 45.31, 45.5,
                   44.68, 45.68, 44.41, 45.36, 43.91, 43.55, 43.64, 45.0]
}
```

---

### Game object — final game example

A completed game has `"status": "final"` and a `null` `live` block.

```json
{
  "id": 1005,
  "away": {
    "code": "CHI",
    "name": "Chicago Blackhawks",
    "record": "14-30-3",
    "l10": "3-6-1"
  },
  "home": {
    "code": "PIT",
    "name": "Pittsburgh Penguins",
    "record": "22-21-5",
    "l10": "4-5-1"
  },
  "start": "2026-05-17T00:30:00Z",
  "venue": "PPG Paints Arena",
  "status": "final",
  "live": null,
  "ml": { "away": 175, "home": -210 },
  "ml_open": { "away": 185, "home": -220 },
  "implied": { "away": 36.0, "home": 64.0 },
  "fair": { "away": 34.5, "home": 65.5 },
  "edge": -1.5,
  "movement_24h": [37.36, 37.28, 37.4, 37.62, 36.03, 35.1, 36.46, 37.27,
                   35.92, 35.36, 34.47, 35.76, 35.18, 35.6, 36.39, 35.65,
                   35.66, 34.97, 35.69, 35.02, 36.06, 37.28, 36.57, 36.0]
}
```

---

### Game object field reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | NHL API game ID (e.g. `2026020042`). Demo IDs use the range 1001–1008. |
| `away` | `object` | Away team descriptor — see Team object below. |
| `home` | `object` | Home team descriptor — see Team object below. |
| `start` | `string \| null` | ISO 8601 UTC puck-drop time. `null` if the NHL API did not supply one. |
| `venue` | `string` | Arena name (e.g. `"TD Garden"`). Empty string when unavailable. |
| `status` | `string` | One of `"scheduled"`, `"live"`, or `"final"`. |
| `live` | `object \| null` | Populated for `status == "live"`; `null` otherwise. See Live block below. |
| `ml` | `object \| null` | Current moneyline odds. `null` when no odds snapshot is available. |
| `ml_open` | `object \| null` | Opening moneyline odds (oldest OddsSnapshot for this game). `null` when unavailable. |
| `implied` | `object` | Vig-adjusted implied win probabilities in percentage points (0–100), derived from `ml`. Always present; defaults to `{away: 50.0, home: 50.0}` when `ml` is `null`. |
| `fair` | `object` | Model fair-value win probabilities in percentage points (0–100). Falls back to `implied` when no `ModelFair` row exists. |
| `edge` | `float \| null` | Away team edge in percentage points: `fair.away − implied.away`. Positive = away team is undervalued. `null` when `ml` is absent. |
| `movement_24h` | `array` | Ordered list of `away_implied` floats from OddsSnapshot rows — see Sparkline section. |

#### Team object

```json
{ "code": "TOR", "name": "Toronto Maple Leafs", "record": "24-18-4", "l10": "6-3-1" }
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | `string` | Three-letter NHL team abbreviation (e.g. `"TOR"`). |
| `name` | `string` | Full team name (e.g. `"Toronto Maple Leafs"`). |
| `record` | `string` | Season record in W-L-OT format. Empty string `""` in v1 (populated by future history feature). |
| `l10` | `string` | Last-10-games record. Empty string `""` in v1. |

#### Moneyline object (`ml` / `ml_open`)

```json
{ "away": 120, "home": -140 }
```

| Field | Type | Description |
|-------|------|-------------|
| `away` | `integer` | Away team American moneyline odds. Positive = underdog (e.g. `+120`), negative = favourite (e.g. `-140`). |
| `home` | `integer` | Home team American moneyline odds. Same sign convention as `away`. |

#### Live block

Present only when `status == "live"`.

```json
{
  "period": "2nd",
  "clock": "12:34",
  "away_score": 3,
  "home_score": 2,
  "away_sog": 18,
  "home_sog": 22
}
```

| Field | Type | Description |
|-------|------|-------------|
| `period` | `string` | Current period label (e.g. `"1st"`, `"2nd"`, `"3rd"`, `"OT"`). |
| `clock` | `string` | Remaining time in the period in `MM:SS` format (e.g. `"12:34"`). |
| `away_score` | `integer` | Away team goals scored so far. |
| `home_score` | `integer` | Home team goals scored so far. |
| `away_sog` | `integer \| null` | Away team shots on goal. `null` until the live feed provides it. |
| `home_sog` | `integer \| null` | Home team shots on goal. `null` until the live feed provides it. |

---

### Sparkline — `movement_24h`

`movement_24h` is an array of up to 24 `away_implied` probability floats,
taken from `OddsSnapshot` rows ordered chronologically (oldest → newest).
Each entry represents a single poll sample, spaced ~3 minutes apart.

```json
"movement_24h": [46.38, 44.95, 44.14, 45.07, 44.14, 43.78, 44.91, 44.44,
                 44.9,  45.95, 47.13, 46.81, 45.87, 45.58, 45.31, 45.5,
                 44.68, 45.68, 44.41, 45.36, 43.91, 43.55, 43.64, 45.0]
```

Each `OddsSnapshot` row that feeds this array has the following shape in the
database:

| DB column | API type | Description |
|-----------|----------|-------------|
| `fetched_at` | ISO 8601 UTC timestamp | When the odds were sampled (not exposed directly in the array — order is preserved). |
| `away_ml` | `integer` | Away team American moneyline at this snapshot (e.g. `120`). |
| `home_ml` | `integer` | Home team American moneyline at this snapshot (e.g. `-140`). |
| `away_implied` | `float` | Vig-adjusted implied probability for the away team at this snapshot. This is the value stored in `movement_24h`. |
| `home_implied` | `float` | Vig-adjusted implied probability for the home team (not in the array but stored in DB). |

The array is empty `[]` when no snapshots have been collected for a game.
Values are percentage points (e.g. `45.38` means 45.38 %).

---

## NHL Stats REST API — `GET /stats/rest/en/game`

**Base URL:** `https://api.nhle.com/stats/rest/en`

Returns the full historical game set. Consumed by `get_all_games()` in
`nhl_client.py` and persisted by `ingest_historical_games()` in
`services/historical.py` into the `game` table (Issue #131).

### Response shape

```json
{
  "data": [
    {
      "id": 2026020001,
      "easternStartTime": "07:30 PM",
      "gameDate": "2026-01-10",
      "gameNumber": 1,
      "gameScheduleStateId": 1,
      "gameStateId": 4,
      "gameType": 2,
      "homeScore": 3,
      "homeTeamId": 10,
      "period": 3,
      "season": 20252026,
      "visitingScore": 2,
      "visitingTeamId": 15
    }
  ],
  "total": 65432
}
```

| Field | Type | DB column | Notes |
|-------|------|-----------|-------|
| `id` | `integer` | `game_id` (PK) | NHL numeric game identifier |
| `easternStartTime` | `string` | `eastern_start_time` | e.g. `"07:30 PM"` |
| `gameDate` | `string` | `game_date` | `YYYY-MM-DD` |
| `gameNumber` | `integer` | `game_number` | Sequential within season |
| `gameScheduleStateId` | `integer` | `game_schedule_state_id` | NHL scheduling state code |
| `gameStateId` | `integer` | `game_state_id` | NHL game state code (4 = final) |
| `gameType` | `integer` | `game_type` | 1 = preseason, 2 = regular, 3 = playoffs |
| `homeScore` | `integer` | `home_score` | — |
| `homeTeamId` | `integer` | `home_team_id` | Matches `team.team_id` when seeded |
| `period` | `integer` | `period` | Period at game end or current period |
| `season` | `integer` | `season` | e.g. `20252026` |
| `visitingScore` | `integer` | `away_score` | — |
| `visitingTeamId` | `integer` | `away_team_id` | Matches `team.team_id` when seeded |
| `total` | `integer` | not stored | Pagination envelope field — row count only |

---

## NHL Web API — `GET /v1/roster/{team}/{season}`

**Base URL:** `https://api-web.nhle.com/v1`

Returns the full roster for one team and one season. Consumed by the backfill notebook
(Issue #165) to populate `dim_player`. Players are grouped into three arrays —
`forwards`, `defensemen`, and `goalies` — each element sharing the same per-player
object shape.

### Response shape (abbreviated)

```json
{
  "forwards": [
    {
      "id": 8478402,
      "headshot": "https://assets.nhle.com/mugs/nhl/20252026/EDM/8478402.png",
      "firstName": { "default": "Connor" },
      "lastName": { "default": "McDavid" },
      "sweaterNumber": 97,
      "positionCode": "C",
      "shootsCatches": "L",
      "heightInInches": 73,
      "weightInPounds": 193,
      "heightInCentimeters": 185,
      "weightInKilograms": 88,
      "birthDate": "1997-01-13",
      "birthCity": { "default": "Richmond Hill" },
      "birthCountry": "CAN",
      "birthStateProvince": { "default": "Ontario" }
    }
  ],
  "defensemen": [ ... ],
  "goalies": [ ... ]
}
```

### Per-player object → `dim_player` column mapping

| API field | `dim_player` column | Notes |
|---|---|---|
| `id` | `player_id` | Integer PK — not auto-generated |
| `firstName.default` | `first_name` | English default only |
| `lastName.default` | `last_name` | English default only |
| `sweaterNumber` | `sweater_number` | Overwritten on upsert |
| `positionCode` | `position` | `C` / `L` / `R` / `D` / `G` |
| `shootsCatches` | `shoots_catches` | `L` or `R` |
| `heightInInches` | `height_in_inches` | Integer |
| `weightInPounds` | `weight_in_pounds` | Integer |
| `birthDate` | `birth_date` | `YYYY-MM-DD` string |
| `birthCountry` | `birth_country` | ISO 3-letter code |
| `headshot` | `headshot_url` | CDN URL |

---

## NHL Web API — `GET /v1/gamecenter/{game_id}/boxscore` → player stats fields

**Base URL:** `https://api-web.nhle.com/v1`

The `playerByGameStats` block of the boxscore response feeds `fact_skater_stats` and
`fact_goalie_stats` (Issue #169). It is nested under `awayTeam` and `homeTeam`, each of
which has `forwards`, `defense`, and `goalies` arrays.

### Skater object shape (forwards and defense)

```json
{
  "playerId": 8478402,
  "sweaterNumber": 97,
  "name": {
    "firstName": { "default": "Connor" },
    "lastName":  { "default": "McDavid" }
  },
  "position": "C",
  "goals": 1,
  "assists": 2,
  "points": 3,
  "plusMinus": 1,
  "pim": 0,
  "toi": "22:34",
  "hits": 2,
  "blockedShots": 1,
  "powerPlayGoals": 1,
  "powerPlayPoints": 2,
  "shorthandedGoals": 0,
  "faceoffWinningPctg": 52.4,
  "giveaways": 1,
  "takeaways": 2,
  "shifts": 26
}
```

### Goalie object shape

```json
{
  "playerId": 8476945,
  "sweaterNumber": 35,
  "name": {
    "firstName": { "default": "Ilya" },
    "lastName":  { "default": "Samsonov" }
  },
  "toi": "60:00",
  "goalsAgainst": 1,
  "saveShotsAgainst": "29/30",
  "savePctg": 0.9667,
  "evenStrengthShotsAgainst": 22,
  "powerPlayShotsAgainst": 5,
  "shorthandedShotsAgainst": 3,
  "pim": 0,
  "starter": 1,
  "decision": "W"
}
```

`saveShotsAgainst` is the API's composite `'saves/shots'` string. The `saves` and
`shots_against` columns in `fact_goalie_stats` are parsed from this string by splitting on
`'/'`. `decision` is absent from backup goalie objects — stored as `NULL` in the DB.

---

## NHL Web API — `GET /v1/player/{player_id}/landing`

**Base URL:** `https://api-web.nhle.com/v1`

Called by `get_player_landing(player_id)` when a player appears in a game's
`playerByGameStats` but has no row in `dim_player`. The `_ensure_dim_player()` function
in `services/player_stats.py` uses this response to create the `dim_player` row before
writing the fact row.

### Response shape (abbreviated)

```json
{
  "playerId": 8478402,
  "firstName": { "default": "Connor" },
  "lastName":  { "default": "McDavid" },
  "sweaterNumber": 97,
  "position": "C",
  "shootsCatches": "L",
  "heightInInches": 73,
  "weightInPounds": 193,
  "birthDate": "1997-01-13",
  "birthCountry": "CAN",
  "headshot": "https://assets.nhle.com/mugs/nhl/20252026/EDM/8478402.png"
}
```

| API field | `dim_player` column | Notes |
|---|---|---|
| `playerId` | `player_id` | Integer PK |
| `firstName.default` | `first_name` | English default only |
| `lastName.default` | `last_name` | English default only |
| `sweaterNumber` | `sweater_number` | Integer |
| `position` | `position` | `C` / `L` / `R` / `D` / `G` |
| `shootsCatches` | `shoots_catches` | `L` or `R` |
| `heightInInches` | `height_in_inches` | Integer |
| `weightInPounds` | `weight_in_pounds` | Integer |
| `birthDate` | `birth_date` | `YYYY-MM-DD` string |
| `birthCountry` | `birth_country` | ISO 3-letter code |
| `headshot` | `headshot_url` | CDN URL string |

---

## Error Responses

All error responses return JSON with a consistent shape and never return
HTML.

### HTTP 404 — Resource not found

```json
{
  "error": "not_found",
  "message": "The requested resource was not found"
}
```

### HTTP 500 — Internal server error

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error` | `string` | Machine-readable error code (`not_found`, `internal_server_error`, `bad_request`). |
| `message` | `string` | Human-readable description of the error. |
