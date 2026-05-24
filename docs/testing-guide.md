# Testing Guide

This guide explains how to run, filter, and measure coverage for both test suites in the NHL Dashboard project.

---

## Backend Tests

Backend tests use **pytest** and live in `tests/`. They target the Flask application in `nhl-dashboard/backend/`.

### Run all backend tests

```bash
pytest
```

### Run a single test file

```bash
pytest tests/test_implied.py -v
```

Replace `test_implied.py` with any file under `tests/`. The `-v` flag prints each test name as it runs.

### Run a single test by name

```bash
pytest tests/test_implied.py::test_implied_probability_home -v
```

### Filter by keyword

```bash
pytest -k "implied" -v
```

---

## Frontend Tests

Frontend tests use **Vitest** with **React Testing Library** and live in `nhl-dashboard/frontend/src/`. All commands must be run from the `nhl-dashboard/frontend/` directory.

```bash
cd nhl-dashboard/frontend
```

### Run all frontend tests

```bash
npm run test
```

This runs `vitest run` (single-pass, non-watch mode) and prints a summary.

### Run in watch mode (re-runs on file save)

```bash
npx vitest
```

### jsdom environment

Tests run in a `jsdom` browser-like environment (configured in `vitest.config.js`). This is required for rendering React components. Do **not** change `environment` to `node`; component tests will fail without `jsdom`.

---

## Coverage

### Backend coverage

```bash
pytest --cov=nhl_dashboard
```

To generate an HTML report:

```bash
pytest --cov=nhl_dashboard --cov-report=html
open htmlcov/index.html
```

### Frontend Coverage

```bash
npm run test:coverage
```

This runs `vitest run --coverage` using the `@vitest/coverage-v8` provider and outputs a summary to the terminal. An HTML report is written to `nhl-dashboard/frontend/coverage/`.

---

## Fixtures

Backend test fixtures are defined in `nhl-dashboard/tests/conftest.py`. They provide:

| Fixture | What it gives you |
|---|---|
| `app` | Flask app wired to a fresh in-memory SQLite database |
| `client` | Flask test client (no real server started) |
| `db` | SQLAlchemy `db` object with an active app context |
| `team_factory` | Creates and commits a `Team` row |
| `game_factory` | Creates and commits a `Game` row with live-game defaults |
| `odds_snapshot_factory` | Creates and commits an `OddsSnapshot` row |
| `model_fair_factory` | Creates and commits a `ModelFair` row |

### Example: using a factory fixture

```python
def test_game_status_live(client, team_factory, game_factory):
    team_factory("TOR", "Toronto Maple Leafs")
    team_factory("BOS", "Boston Bruins")
    game = game_factory("BOS", "TOR", status="LIVE", away_score=1, home_score=2)

    response = client.get("/api/games/today")
    assert response.status_code == 200
    data = response.get_json()
    assert any(g["status"] == "LIVE" for g in data["games"])
```

Factories return the committed model instance, so you can pass `game.id` to `odds_snapshot_factory` or `model_fair_factory` for relational tests.
