# Session Handoff

_Update this file at the end of every session so the next agent can resume cleanly._

---

## Last closed issue

**#122** — Add daily 30-day refresh for NHL historical game updates (2026-05-25)

## MVP completion status

| Feature | Status | Notes |
|---------|--------|-------|
| Live Scoreboard | Done | `/api/games/today` polling via React `usePolling` (30 s) |
| Betting Odds (NHL partner logos) | Done | `nhl_odds_partner` + `nhl_odds_line` tables, seeded from `/v1/score/now` |
| NHL Historical Game Data | Done | `nhl_historical_game` table, daily 30-day refresh |
| Puckline & Totals | Pending | Not started |
| Dollar Return Calculator | Pending | Not started |
| Public Hosting | Pending | Not started |
| Basic Analytics | Pending | Not started |

## Read these first in a new session

1. `harness/AGENTS.md` — coding standards, TDD workflow, directory layout
2. `harness/SPEC.md` — product vision, bet types, MVP feature list
3. `nhl-dashboard/backend/models.py` — all SQLAlchemy models
4. `nhl-dashboard/backend/nhl_client.py` — NHL API wrapper

## Active branches

- `nhl-claude-design` — current development branch (unmerged frontend + design work)
- `main` — stable, all passing tests

## Known open questions

- Public hosting target (Render / Railway / Fly.io) not yet selected.
- Puckline and totals odds not yet sourced from the-odds-api (requires endpoint research).
- Issue #124 (fix Section 3 game table in db_explorer.ipynb) is open.

## How to check next work

```bash
cat feature_list.json | python3 -m json.tool | grep -A4 '"pending"'
gh issue list --state open
```
