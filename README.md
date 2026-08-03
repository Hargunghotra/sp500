# S&P 500 Trading Simulator

Decoupled Next.js + Flask paper trading dashboard with a TradingView dark theme, technical analysis, and VADER news sentiment.

## Structure

- `sp500-backend/` — Flask API (`/api/analyze`)
- `sp500-frontend/` — Next.js App Router dashboard (Zustand + Recharts)

## Run

**Terminal 1 — Backend**

```bash
cd sp500-backend
venv\Scripts\activate
python app.py
```

**Terminal 2 — Frontend**

```bash
cd sp500-frontend
npm run dev
```

Open http://localhost:3000

The Next.js rewrite proxy forwards `/api/*` to `http://127.0.0.1:5000/api/*`.
