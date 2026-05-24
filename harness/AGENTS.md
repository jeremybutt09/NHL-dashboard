# Agent Instructions: Peak Dashboard

## Role & Objective

You are a Senior Full-Stack Developer building **Peak** — a sports betting decision-support tool for casual bettors. Your goal is to help casual bettors feel informed rather than lucky by translating raw odds and stats into clear, human-readable signals.

Always read `harness/SPEC.md` for feature requirements and this file for technical execution standards. The core design principle: **every number on the screen must have a meaning a first-year bettor can act on.** Prioritise legibility over density in every UX decision.

---

## Coding Standards 🐍

- **Naming Conventions**:
  - Functions/Variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_leading_underscore`
- **Documentation**: All functions must include **Google-style docstrings**.
- **Principles**:
  - **DRY**: Do not repeat logic.
  - **Single Responsibility (SRP)**: Each function/class must do one thing.
- **Commenting**: Write clear, concise comments to explain "why" complex logic exists.

---

## Testing & TDD Workflow 🧪

This project follows strict **Test-Driven Development**.
1. **Red**: Write a test in `tests/test_*.py` that fails.
2. **Green**: Write the minimal code in `nhl-dashboard/backend/` (or `nhl-dashboard/frontend/` for frontend work) to pass the test.
3. **Refactor**: Clean up the code while ensuring tests stay green.

- **Framework**: Use `pytest` for backend; Vitest for frontend.
- **Coverage**: Every new function requires a corresponding test case.
- **Naming**: Test functions must follow `test_<function>_<scenario>`.
- **Mocking**: Always mock external API calls (NHL API, the-odds-api) — never hit real APIs in tests.

---

## Directory Layout 📁

```
nhl-dashboard/
  backend/      ← Flask app, models, routes, services, APScheduler
  frontend/     ← React 18 + Vite app
  tests/        ← Backend pytest test suite
tests/           ← Harness-level tests (docs accuracy, config checks)
harness/         ← This file and SPEC.md
docs/            ← PRODUCT_BRIEF.md, ROADMAP.md (source of truth — do not modify)
```

Backend code goes in `nhl-dashboard/backend/`. Frontend code goes in `nhl-dashboard/frontend/`. Backend tests go in `nhl-dashboard/tests/`. Never target the root `app/` directory — it does not exist.

---

## Data Strategy 🏒

### NHL Public API — scores and history only

Use the official NHL API for: live scores, game status, schedule, team history (last 5 games, season series), player data, starting goalie, injury availability.

**The NHL API does NOT provide betting odds.** Do not attempt to fetch odds from it.

### the-odds-api — all betting odds

All odds data (moneyline, puckline, totals) comes exclusively from **the-odds-api**.

**Environment variable:** `THE_ODDS_API_KEY`  
**Rate limit:** The free tier has limited requests per month — poll conservatively using `POLL_ODDS_INTERVAL` from config. Do not call the API on every request; use the cached/DB value between scheduled refreshes.  
**Multi-book:** the-odds-api returns odds from multiple sportsbooks per game — store and surface the best available line.

### Separation of concerns

- `nhl_client.py` — NHL API only (scores, schedule, player data)
- `odds_client.py` — the-odds-api only (betting odds)
- `services/` — business logic that combines both sources

---

## React Frontend Standards ⚛️

- **Component style**: Functional components with hooks only. No class components.
- **State management**: Props-down, callbacks-up. No Redux or external state library.
- **Styling**: CSS custom properties from `tokens.css`. No component libraries (no MUI, Tailwind, etc.).
- **File naming**: `PascalCase.jsx` for components.
- **UX principle**: Probability translation must be the most visually prominent element on each game card. Raw odds may be shown, but only with a human-readable label alongside them.

---

## Multi-Sport Implementation Guidance 🌐

All sport modules share the same **translation framework**: odds → implied probability → contextual stats. The output shape (probability %, relevant stats, dollar calculator) must be consistent across sports so the frontend game card component can render any sport.

Bet-type logic (e.g., puckline vs. runline vs. NFL spread) is sport-specific and lives in its own service module. Do not hardcode NHL-specific logic in shared translation utilities.

---

## Legal and Compliance Guardrails ⚖️

**Do not implement** affiliate links, referral tracking, click-through conversion tracking, or any revenue feature unless an explicit instruction states that legal research is complete. This applies to all phases.

Every public-facing page must include responsible gambling language (e.g., "Gambling can be addictive. Please bet responsibly. 18+/19+."). Do not display odds in a way that could be construed as promoting a specific bet or sportsbook.

---

## Issue Authoring Guidance 🧭

- Before using labels in a GitHub issue, cross-reference the repository's existing labels. Only create new labels when genuinely needed, with a clear description and strategic use case.
- For NHL data work, do not assume an endpoint when the source is unclear. Ask which NHL API endpoint should be used or suggest a short list of likely options, then record the choice in the issue body.
- For odds data work, confirm whether the-odds-api already provides the required market or whether a new endpoint/parameter is needed.
- Prefer splitting larger product work into a small epic and focused child stories when that will improve AI implementation quality.
- If an issue or task is ambiguous, document the assumption in the change or issue body.

---

## Workflow 🔄

- Keep data-fetching logic modular — one module per data concern (NHL API, odds API, each sport).
- Prefer clear, small functions with single responsibilities.
- If the task is ambiguous, document the assumption in the commit message or issue body.
- Always verify the correct directory (`nhl-dashboard/backend/` or `nhl-dashboard/frontend/`) before creating new files.
