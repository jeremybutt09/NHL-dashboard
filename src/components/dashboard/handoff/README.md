# Peak NHL Dashboard — Handoff Package

Everything Claude Code needs to build this for real.

## What's in this folder

| File | Purpose |
|---|---|
| `HANDOFF.md` | Full architecture spec — stack, folder layout, models, endpoints, math |
| `PROMPT.md` | The exact prompt to paste into Claude Code, broken into phases |
| `Dashboard.html` | The working React prototype — visual source of truth |
| `reference-dashboard.png` | Rendered screenshot of the prototype |
| `README.md` | This file |

## How to use it

1. **Download this whole folder** (the chat has a download button below).
2. Open a fresh terminal in a new project directory.
3. Start Claude Code in that directory.
4. Copy `Dashboard.html`, `HANDOFF.md`, and `reference-dashboard.png` into the directory so Claude Code can read them.
5. Open `PROMPT.md`, copy the prompt block, paste it to Claude Code.
6. Claude Code will scaffold the project in 4 phases — review each phase before continuing.

## Stack summary

- **Backend:** Flask + Flask-SQLAlchemy + SQLite + APScheduler + httpx
- **Frontend:** React 18 + Vite + plain CSS
- **Data:** Public NHL API (no key needed) + a stub odds client for v1
- **Updates:** Polling every 15s for live games, every 5 min for the slate

## Running the result

After Claude Code builds it:

```bash
# Backend (terminal 1)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## When you want to extend it

- **Real odds provider:** swap the stub in `backend/odds_client.py` for The Odds API (free tier).
- **Player props / totals:** add columns to `OddsSnapshot`, new cells in the table.
- **Mobile layout:** add breakpoints in `app.css`, collapse the table into cards under 900px.
- **Real fair-value model:** replace `services/implied.py:compute_fair` with whatever model you build.
