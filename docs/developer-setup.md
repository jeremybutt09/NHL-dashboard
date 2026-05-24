# Developer Setup and Local Deployment Guide

This guide walks a new developer through getting the NHL Dashboard running locally in under 10 minutes.

## Prerequisites

- **Python 3.10+** (3.13 recommended)
- **Node.js 18+** and **npm**
- **git**

---

## Backend Setup

The backend is a Flask 3 application located in `nhl-dashboard/backend/`.

### 1. Create and activate a virtual environment

```bash
cd nhl-dashboard/backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Flask backend

```bash
flask --app app run --debug
```

By default Flask listens on port 5000. On macOS, port 5000 is occupied by AirPlay Receiver — see [Troubleshooting](#troubleshooting) below if this affects you.

---

## Frontend Setup

The frontend is a React 18 + Vite application located in `nhl-dashboard/frontend/`.

### 1. Install frontend dependencies

```bash
cd nhl-dashboard/frontend
npm install
```

### 2. Start the Vite dev server

```bash
npm run dev
```

The dev server starts at **http://localhost:5173** and proxies all `/api` requests to the Flask backend (default: `http://localhost:5001`).

---

## Running Both Together

Open two terminal tabs:

| Terminal | Command |
|---|---|
| Tab 1 — backend | `cd nhl-dashboard/backend && source .venv/bin/activate && FLASK_RUN_PORT=5001 flask --app app run --debug` |
| Tab 2 — frontend | `cd nhl-dashboard/frontend && npm run dev` |

Then open **http://localhost:5173** in your browser.

---

## Configuration

All configuration is read from environment variables at startup. The following variables are supported:

| Variable | Default | Description |
|---|---|---|
| `FLASK_RUN_PORT` | `5000` | Port the Flask dev server listens on. Set to `5001` on macOS to avoid the AirPlay conflict. |
| `DATABASE_URL` | `sqlite:///instance/nhl.db` (relative to `backend/`) | SQLAlchemy database URI. Override to use a different SQLite path or a PostgreSQL URL. |
| `SECRET_KEY` | `dev-secret-key` | Flask secret key. **Must be changed in production.** |
| `POLL_SLATE_INTERVAL` | `300` | Seconds between NHL schedule polls (slate refresh job). |
| `POLL_LIVE_INTERVAL` | `15` | Seconds between live score polls. |
| `POLL_ODDS_INTERVAL` | `300` | Seconds between odds polls. |
| `COMPUTE_FAIR_INTERVAL` | `300` | Seconds between fair-value recalculation runs. |
| `PRUNE_INTERVAL` | `3600` | Seconds between old-snapshot pruning runs. |

Example — start backend on port 5001 with a custom DB path:

```bash
export FLASK_RUN_PORT=5001
export DATABASE_URL=sqlite:////tmp/nhl-dev.db
flask --app app run --debug
```

---

## CORS

`app.py` adds a hardcoded `Access-Control-Allow-Origin` header for the Vite dev server:

```python
response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
```

If you run the Vite server on a non-default port (e.g., `npm run dev -- --port 5174`), update that line in `nhl-dashboard/backend/app.py` to match. The `vite.config.js` proxy target must also be updated to point at the Flask port you chose.

---

## Troubleshooting

### macOS: Port 5000 conflict (AirPlay Receiver)

macOS Monterey and later bind port 5000 to the AirPlay Receiver service. Starting Flask without setting a different port will fail with `Address already in use`.

**Fix A — use a different port (recommended):**

```bash
FLASK_RUN_PORT=5001 flask --app app run --debug
```

The project's `vite.config.js` already proxies to `http://localhost:5001`, so no frontend change is needed.

**Fix B — disable AirPlay Receiver:**

1. Open **System Settings → General → AirDrop & Handoff**
2. Toggle **AirPlay Receiver** off

Flask can then run on the default port 5000, but you must update `vite.config.js`:

```js
target: 'http://localhost:5000',
```

### `ModuleNotFoundError` on `flask --app app run`

Make sure your virtual environment is activated (`source .venv/bin/activate`) and you ran `pip install -r requirements.txt` inside it.

### Frontend shows a blank page or network errors

1. Confirm the backend is running and accessible at the port referenced in `vite.config.js`.
2. Check the browser console for CORS errors — the `Access-Control-Allow-Origin` header must match the Vite origin (default `http://localhost:5173`).
