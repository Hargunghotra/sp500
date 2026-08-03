# S&P 500 Trading Simulator

Decoupled Next.js + Flask autonomous paper desk with a glassy TradingView-inspired UI, S&P 500 screening, Gemini strategy, and portfolio equity tracking.

## Setup

1. Copy `sp500-backend/.env.example` → `sp500-backend/.env` and set `GEMINI_API_KEY`.
2. `pip install -r sp500-backend/requirements.txt`

## Run

```bash
# Terminal 1
cd sp500-backend
venv\Scripts\activate
python app.py

# Terminal 2
cd sp500-frontend
npm run dev
```

Open http://localhost:3000

## Autonomy

Each cycle:
1. Screens the S&P 500 locally (technicals + patterns; news on shortlist)
2. Asks Gemini for sector/style strategy + BUY/SELL/HOLD on top candidates
3. Executes paper trades into a **$50,000** book
4. Writes equity snapshots + AI trade reports

Use **Start 24/7** / **Run once**, or **Reset book to $50,000**.
