# S&P 500 Trading Simulator

Decoupled Next.js + Flask paper trading dashboard with a TradingView dark theme, technical analysis, VADER news sentiment, and an autonomous Gemini trading agent.

## Structure

- `sp500-backend/` — Flask API, persistent ledger, AI agent + scheduler
- `sp500-frontend/` — Next.js dashboard (Zustand + Recharts)

## Setup

1. Copy `sp500-backend/.env.example` to `sp500-backend/.env` and set `GEMINI_API_KEY`.
2. Backend deps (if needed):

```bash
cd sp500-backend
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

**Terminal 1 — Backend (must stay running for 24/7 agent)**

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

## Autonomous agent

- Start/Stop and **Run once** from the AI Trade Agent panel.
- Cycles scan the watchlist, ask **Gemini** for BUY/SELL/HOLD + reasoning, apply risk caps, execute paper trades, and append reports to `sp500-backend/data/reports.jsonl`.
- Portfolio lives in `sp500-backend/data/portfolio.json` (shared by AI + manual trades).
- Default schedule: every 15 minutes during US regular hours (set `ALLOW_AFTER_HOURS=true` to trade outside the session).
