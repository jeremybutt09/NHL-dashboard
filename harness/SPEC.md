# Peak — Agent-Facing Product Spec

_Source of truth: `docs/PRODUCT_BRIEF.md` and `docs/ROADMAP.md`. This file is a distillation for AI agent sessions._

---

## Product Vision

**Peak** is a sports betting insights dashboard that translates raw odds and team stats into clear, human-readable signals — helping casual bettors feel informed rather than lucky.

Peak does **not** take bets. It is a **decision-support tool**. Users arrive, evaluate a game, understand what the market is pricing in, compare it against relevant stats, and then go place their bet at a sportsbook of their choice.

**Positioning headline:** _"Bet with a reason, not a guess."_

**Core design principle:** Every number on the screen must have a meaning a first-year bettor can act on.

---

## Target User

**Primary:** Men aged 19–35, US and Canada, betting 2–3 times per week. They enjoy sports, follow their teams, and are comfortable with basic stats. They are **not** sharp bettors, arbitrage players, or professional gamblers. The product should not try to serve those users.

**Secondary:** Women and older men who match the same interest profile.

---

## Core Features (MVP — Phase 0, NHL)

### 1. Game Card with Three Bet Types

Each game card must support three bet types with a human-readable probability translation for each:

**Moneyline** — _Who wins?_
- Implied win probability from the moneyline odds (e.g., "Market gives the Leafs a 62% chance")
- Season series H2H record
- Last 5 game results for each team
- Starting goalie
- Key injury/availability flags

**Puckline (Spread)** — _Does the favourite win by more than 1.5, or does the underdog keep it close?_
- Implied cover probability from the puckline odds
- Cover rate as favourite vs. underdog (split stat)
- Last 5 spread results
- Dollar return calculator: "Bet $10 → win $Y if correct"

**Total (Over/Under)** — _Combined goals above or below X?_
- Implied over/under probability
- Average combined goals in last 5 games for each team
- Starting goalie save %
- Last 5 totals trend (O/U result per game)

**Props (Phase 2+):** Deferred — individual player performance bets are out of MVP scope.

### 2. Dollar Return Calculator

User inputs a bet amount and sees the projected payout for any bet type. Required for MVP.

### 3. Live Scoreboard

All NHL games today with real-time score updates and game status (pre-game, live, final).

### 4. Public Hosting (Epic 0.5)

The app must be on a real public URL before the MVP is considered complete. Target providers: **Render, Railway, or Fly.io** (target <$20/mo).

### 5. Basic Analytics (Epic 0.6)

Lightweight analytics to track real users. Preference: **Plausible or PostHog** over Google Analytics.

---

## Odds Data Source

**Odds come from [the-odds-api](https://the-odds-api.com)** — real-time odds from multiple sportsbooks via a single API.

The NHL public API is **only** used for scores, game status, team history, and player data. It does **not** provide betting odds. This distinction is critical for implementation.

---

## Technical Architecture

| Layer | Choice |
|---|---|
| Backend | Python / Flask |
| Database | SQLite + SQLAlchemy |
| Background jobs | APScheduler |
| Live scores | NHL Public API |
| Live odds | the-odds-api (real-time) |
| Frontend | React 18 + Vite |
| Styling | CSS custom properties (tokens.css) |
| Hosting | Render / Railway / Fly.io (target <$20/mo) |
| Analytics | Plausible or PostHog |

**Directory layout:**
- Backend: `nhl-dashboard/backend/`
- Frontend: `nhl-dashboard/frontend/`
- Tests: `nhl-dashboard/tests/` (backend) and `tests/` (harness-level)

---

## Sport Rollout

The translation framework (odds → probability → contextual stats) is reusable, but each sport has different data sources and bet-type logic.

| Phase | Sport | Target |
|---|---|---|
| Phase 0 (MVP) | NHL | May–June 2026 (playoffs) |
| Phase 1 | NHL polish + MLB | June–August 2026 |
| Phase 2 | NFL + NBA | Fall 2026 |
| Phase 3 | Monetization | TBD — requires legal research first |
| Phase 4 | Player Props | TBD |

---

## Monetization

MVP will **not** be monetized. Planned sequence: display ads (no legal barrier) → sportsbook affiliate (requires legal research) → freemium (only if user base warrants it).

**Legal gate:** Do not implement affiliate links, referral tracking, or any revenue feature until legal and regulatory research is complete. This is non-negotiable.

---

## MVP Success Metrics

- 10+ real users provide qualitative feedback
- Users can correctly interpret at least 2 of 3 bet types without explanation
- Odds data is accurate and updates within 5 minutes of line movement
- App is accessible on desktop

---

## NHL API Selection Guidance

- Use the official NHL API for **scores, game status, team history, and player data only**.
- When a feature needs NHL data and the exact endpoint is not obvious, ask which endpoint should be used or suggest a short list of options before implementation.
- Record the chosen endpoint in the issue body so the implementation target is explicit.
- Keep odds display, stats display, and game status as separate concerns in separate modules when possible.
