# NHL Dashboard

Live NHL scores, moneyline odds, implied probabilities, and model edge calculations.

## Running locally

### Backend (Flask — port 5000)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

### Frontend (Vite — port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. All `/api` requests are proxied to the Flask backend at `:5000`.
