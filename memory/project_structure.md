---
name: project-structure
description: Core layout of the NHL Dashboard project — directories, key files, and conventions established in Issue #1.
metadata:
  type: project
---

Flask-based NHL Betting & Scores Dashboard (Python 3.9+).

**Why:** Built to display live scores, money-line odds, and team history for daily NHL games.

**How to apply:** All new skills go in `app/agents/`, all tests in `tests/test_*.py`. Follow TDD strictly per [[tdd-standards]].

## Layout
```
app/
  __init__.py
  agents/
    __init__.py
    nhl_client.py    # ← first skill (Issue #1)
tests/
  __init__.py
  test_nhl_client.py
harness/
  SPEC.md            # product requirements
  AGENTS.md          # coding/TDD standards
requirements.txt     # flask, requests, pytest
pytest.ini           # testpaths = tests
```

## NHL API
- Scoreboard endpoint: `https://api-web.nhle.com/v1/scoreboard/now`
- Response: `{ focusedDate, focusedDateCount, gamesByDate: [{date, games:[...]}] }`
- `get_todays_games()` filters `gamesByDate` by `focusedDate` to return today's games.
