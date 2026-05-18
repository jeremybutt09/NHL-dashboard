# NHL Dashboard

Full-stack NHL scores and betting odds dashboard — Flask backend + React/Vite frontend.

## Running the backend (:5000)

```bash
cd nhl-dashboard/backend
pip install -r requirements.txt
flask run
```

The API will be available at `http://localhost:5000`.  
Health check: `http://localhost:5000/api/health`

## Running the frontend (:5173)

```bash
cd nhl-dashboard/frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173`.  
API calls to `/api/*` are proxied to the backend on port 5000.

## Verifying the proxy

With both servers running, open the browser console on `http://localhost:5173` and run:

```js
fetch('/api/health').then(r => r.json()).then(console.log)
// => { ok: true, db: "connected", last_poll: null }
```
