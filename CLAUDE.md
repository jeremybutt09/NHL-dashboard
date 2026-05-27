# NHL Dashboard — Claude Code Instructions

## Read these first

Before making any changes, read:
- `harness/AGENTS.md` — coding standards, TDD workflow, naming conventions
- `harness/SPEC.md` — product vision and MVP feature list

## Project summary

**Peak** is a Flask + React 18 sports betting decision-support dashboard for casual NHL bettors.

- **Backend** (`nhl-dashboard/backend/`): Flask app, SQLAlchemy/SQLite, APScheduler background jobs.
- **Frontend** (`nhl-dashboard/frontend/`): React 18 + Vite, polling `/api/games/today` every 30 s via `usePolling`.
- **NHL data**: `/v1/schedule/now` (today's slate) and `/v1/score/now` (live scores + partner odds) via `nhl_client.py`.
- **Odds data**: all moneyline/puckline/total odds come exclusively from **the-odds-api** via `odds_client.py`.
- **Active API endpoints**: `GET /api/health`, `GET /api/games/today`, `GET /api/games/<game_id>`.
- **Background jobs** (APScheduler): `refresh_schedule`, `refresh_slate`, `refresh_scores`, `refresh_odds`, `prune_nhl_odds_lines`, `ingest_historical_games`, `refresh_recent_historical_games`.
- **Quality gate**: `./init.sh` — installs deps and runs `pytest tests/`.
- **New sessions**: read `session-handoff.md` → `feature_list.json` → `RESUME-GUIDE.md`.

## Mandatory workflow for every change

1. **Red** — write a failing test in `tests/test_*.py`
2. **Green** — write minimal code in `app/` to pass it
3. **Refactor** — clean up, confirm all tests still pass

## Commit format

```
<short description> (Issue #N)

Closes #N
```

## Interactive session permissions

`.claude/settings.json` pre-approves common low-risk tools (file reads/writes, pytest, safe git commands) so developers are not interrupted by repetitive permission prompts during normal work. Destructive operations (`rm -rf`, force-push, hard reset) are explicitly denied. Do not add blanket `Bash` approval to this file.

## User stories

Whenever a user story is created (via the `/user-story` skill or any other method), immediately upload it to GitHub as an issue using `gh issue create`. The issue body should contain the full user story text including acceptance criteria. Do not wait to be asked — creating the GitHub issue is the final step of every user story creation, without exception. These issues are intended to be completed later by an AI agent running `./scripts/process-issues.sh`.

**Do not implement the user story after creating the issue.** Stop after the issue is created. The GitHub issue is a work queue entry for `./scripts/process-issues.sh` to process in a future session — not a signal to start coding now.

## Automated issue processing

To run all open GitHub issues sequentially through Claude Code (headless):

```bash
./scripts/process-issues.sh
```

To start from a specific issue number (e.g., after a failure at #7):

```bash
./scripts/process-issues.sh 7
```

Each run opens a fresh Claude session per issue, commits, and closes the issue on GitHub before moving on. See `scripts/issue-prompt.md` for the per-session instructions Claude receives.

## Database schema changes

Any time the database structure changes — column renamed, table added or removed, column added or dropped — you **must** update all five of the following before committing:

1. **`docs/database-schema.md`** — reflect the new/renamed/removed table or column in every relevant table definition.
2. **`docs/api-field-mappings.md`** — update the mapping between the source API field and the database column name wherever the change applies.
3. **`docs/api-response-examples.md`** — update any example JSON snippets or field lists that reference the old name or shape.
4. **`docs/data-pipeline.md`** — update the pipeline description (ingestion steps, transform logic, field names) to match the new structure.
5. **`nhl-dashboard/notebooks/db_explorer.ipynb`** — update any cells that reference the old column/table names so the notebook runs cleanly against the new schema. For a new table, add a cell that queries it and briefly describes what it contains, what API endpoint populates it, and where in the pipeline that happens.

These updates are **part of the same commit as the schema change** — they are not follow-up work. Do not close the issue or mark the task done until all five documents are consistent with the new schema.

## AI session state

The `memory/` directory is intentionally gitignored. It contains auto-generated context files written by Claude during agent runs and is not source code. Do not commit or force-track files under `memory/`.
