# Peak — Progress Log

_Human-readable changelog of sessions and decisions. Update at the end of every issue._

---

## Current state (2026-06-08)

**MVP status:** MVP complete as of Issue #122 (2026-05-25). Live Scoreboard, Betting Odds
(the-odds-api), and NHL Historical Game Data are fully implemented and merged to `main`.

**Active NHL API endpoints:**

| Endpoint | Client function | Used for |
|----------|-----------------|---------|
| `/v1/schedule/now` | `get_schedule_now()` | Today's game slate |
| `/v1/score/now` | `get_score_now()` | Live scores + partner odds |
| `/v1/gamecenter/<id>/boxscore` | `get_boxscore(game_id)` | Per-game boxscore |
| `https://api.nhle.com/stats/rest/en/game` | `get_all_games()` | Historical game list |
| `https://api.nhle.com/stats/rest/en/team` | `get_all_teams()` | Full team list |

**Post-MVP backlog:** Puckline & Totals, Dollar Return Calculator, Public Hosting, Basic Analytics.

---

## Session log

### 2026-06-08 — Issue #174

- Weekly harness review — created `harness/progress.md`, added `python3 -m pytest` run
  command to `CLAUDE.md`, added `memory/` directory to Step 0 read list in
  `scripts/issue-prompt.md`, updated `session-handoff.md` to last issue #174.

### 2026-06-01 — Issue #161

- Weekly harness review — added explicit `python -m pytest tests/` run command to
  `harness/AGENTS.md`, added `## Status` section to `harness/SPEC.md` marking MVP complete,
  added ai-skills submodule documentation to `CLAUDE.md`, updated
  `memory/project_structure.md` (current test files, models, removed stale entries),
  updated `session-handoff.md` to last issue #161.

### 2026-05-25 — Issues #119–#123

- **#119**: Created `nhl_odds_line` table to capture per-game, per-partner odds from `/v1/score/now`.
- **#120**: Added NHL API Odds section to `db_explorer.ipynb` (Section 7).
- **#121**: Ingested NHL historical game data into `nhl_historical_game` table via `get_all_games()`.
- **#122**: Added daily 30-day refresh for NHL historical game updates (`refresh_recent_historical_games`).
- **#123**: Weekly harness review — removed stale test files, created `feature_list.json`,
  `init.sh`, `session-handoff.md`, `RESUME-GUIDE.md`, added DoD to `harness/AGENTS.md`,
  updated `CLAUDE.md` project summary and `scripts/issue-prompt.md` reading list.

### 2026-05-24 — Issues #109–#118

- **#109**: Updated `harness/AGENTS.md` and `harness/SPEC.md` to reflect Product Brief and Roadmap.
- **#110**: Fixed `db_explorer.ipynb` DB_PATH to work from any launch directory (pathlib).
- **#111–#113**: Migrated `Team` model to full NHL Stats API schema; seeded teams at startup.
- **#114**: Updated `db_explorer.ipynb` to query expanded team table fields.
- **#115**: Renamed `game.id` → `game_id` across full stack.
- **#116**: Used `/v1/schedule/now` as sole source for today's game slate.
- **#117**: Replaced per-game boxscore polling with `/v1/score/now` for live score updates.
- **#118**: Created `nhl_odds_partner` table from `oddsPartners` array in `/v1/score/now`.

### 2026-05-23 — Issues #93–#108

- Frontend React build (Vitest tests, component suite, odds sparkline, FilterBar, usePolling),
  docs rewrite, harness consolidation, CI pipeline, and Jupyter notebook creation.

### Earlier — Issues #1–#92

- Issues #1–#22: Flask backend, NHL client, scoring, odds integration, Jinja2 dashboard.
- Issues #80–#92: Project restructure from root `app/` to `nhl-dashboard/` layout.
