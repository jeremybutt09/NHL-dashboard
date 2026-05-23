# Claude Code Prompt — Peak NHL Dashboard

Copy the entire block below into Claude Code. Have these files in the same directory when you run it:

- `HANDOFF.md` (architecture spec)
- `Dashboard.html` (the visual prototype — visual source of truth)
- `reference-dashboard.png` (rendered screenshot for reference)

---

```
I want to build a real implementation of an NHL games dashboard. The full
spec is in HANDOFF.md — read it before doing anything else. The visual
source of truth is Dashboard.html (a single-file React prototype with all
styles inline) and reference-dashboard.png (a screenshot).

Stack: Flask + SQLAlchemy + SQLite on the backend. React 18 + Vite on the
frontend. Plain CSS lifted from the prototype — no Tailwind, no component
library. APScheduler for polling, httpx for HTTP, polling-based live
updates (no websockets).

Please proceed in these phases. Stop after each phase and show me what you
have before moving on.

PHASE 1 — SCAFFOLD
  1. Create the folder layout exactly as described in §2 of HANDOFF.md.
  2. backend/ — Flask app factory, SQLAlchemy models from §3, empty route
     stubs, requirements.txt with pinned versions.
  3. frontend/ — Vite + React scaffold, vite.config.js with /api proxy,
     empty component files.
  4. README.md at the root with run instructions for both servers.
  5. Verify: `flask run` starts cleanly, `npm run dev` starts cleanly,
     hitting /api/health returns ok.

PHASE 2 — BACKEND DATA
  1. Implement nhl_client.py against the public NHL API (see §6). Pay
     attention to caching with cachetools.TTLCache.
  2. Implement services/slate.py — pulls today's schedule, upserts Game
     rows. Implement services/live.py — updates live scores.
  3. Implement services/implied.py with the math from §8.
  4. Implement odds_client.py as a STUB that returns deterministic mock
     odds (use the SLATE constant from Dashboard.html as your fixtures).
     The frontend should render perfectly without a real odds provider.
  5. Wire up scheduler.py (APScheduler) with the four jobs from §5.
  6. Implement GET /api/games/today returning the exact JSON shape from §4.
  7. Verify: curl /api/games/today returns a populated slate with live
     status, scores, ml, implied %, edge, and 24h movement array.

PHASE 3 — FRONTEND
  1. Lift the CSS variables from Dashboard.html's :root and .dark blocks
     into styles/tokens.css.
  2. Lift the component-level CSS (.chip, .icon-btn, .live-dot, .game-row,
     keyframes, etc.) into styles/app.css.
  3. Port these components VERBATIM from the prototype's JSX (they already
     render correctly — don't redesign): PeakMark, TeamGlyph, LiveDot,
     Sparkline, ImpliedBar, StatusCell, MatchupCell, MoneylineCell,
     SparklineCell, EdgeCell. Convert inline-style objects to className
     where reasonable but keep the exact visual output.
  4. Build hooks/usePolling.js — fetch on an interval, pause when tab
     hidden via document.visibilityState.
  5. App.jsx polls /api/games/today every 15s and passes games down to
     SlateTable.
  6. Topbar with dark-mode toggle (toggles .dark on <html>, persists in
     localStorage).
  7. Verify: page matches reference-dashboard.png at 1440px wide. Live
     games animate (the shimmer on the implied bar, the pulsing red dot).

PHASE 4 — POLISH
  1. Empty state when no games today.
  2. Loading skeletons (use the existing .bar-shimmer animation).
  3. Error toast if /api/games/today fails — auto-retry on next poll.
  4. Hook up density toggle (compact / regular / comfy) — matches the
     prototype's tweaks.

DESIGN FIDELITY RULES
  - Geist + Geist Mono fonts from Google Fonts (already linked in the
    prototype's <head>).
  - All numbers in monospace with tabular-nums.
  - Team logos from https://assets.nhle.com/logos/nhl/svg/{CODE}_light.svg
    with the colored-chip fallback from TeamGlyph.
  - Do NOT introduce new colors. Every color must come from a CSS var
    defined in tokens.css.
  - Do NOT add icons that aren't in the prototype.
  - Desktop only — 1280px minimum width, no responsive breakpoints needed.

WHEN STUCK
  - The prototype is authoritative for visuals. If HANDOFF.md and
    Dashboard.html disagree, follow Dashboard.html and tell me.
  - The NHL API is undocumented but stable. If an endpoint shape surprises
    you, log the response and ask me before guessing.
  - Don't add dependencies not listed in HANDOFF.md without asking.
```

---

## After Claude Code finishes

Run it locally:

```bash
# Terminal 1 — backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug

# Terminal 2 — frontend
cd src/components/dashboard
npm install
npm run dev
```

Then open http://localhost:5173.
