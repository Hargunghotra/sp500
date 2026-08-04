# S&P 500 Trading Simulator

Decoupled Next.js + Flask autonomous paper desk with a glassy TradingView-inspired UI, S&P 500 screening, Gemini strategy, and portfolio equity tracking.

## Setup (local)

1. Copy `sp500-backend/.env.example` → `sp500-backend/.env` and set `GEMINI_API_KEY`.
2. `pip install -r sp500-backend/requirements.txt`

## Run (local)

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

One-shot cycle (same as Actions):

```bash
cd sp500-backend
python run_cycle.py          # respects US market hours
python run_cycle.py --force  # run anytime
```

## Autonomy (local UI)

Each cycle:
1. Screens the S&P 500 locally (technicals + patterns; news on shortlist)
2. Asks Gemini for sector/style strategy + BUY/SELL/HOLD on top candidates
3. Executes paper trades into a **$50,000** book
4. Writes equity snapshots + AI trade reports

Use **Start 24/7** / **Run once**, or **Reset book to $50,000**.

## Free 24/7 via GitHub Actions (PC can be off)

The workflow [`.github/workflows/agent-cron.yml`](.github/workflows/agent-cron.yml) runs the agent on GitHub-hosted runners and persists the ledger on an `agent-data` branch (ephemeral runners cannot keep local JSON otherwise).

### Enable

1. Push this repo to GitHub (already: `Hargunghotra/sp500`).
2. Repo **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GEMINI_API_KEY`
   - Value: your Gemini API key
3. Optional **Variables** (Settings → Secrets and variables → Actions → Variables):
   - `ALLOW_AFTER_HOURS=true` — trade nights/weekends (default off; schedule still uses `force=false`)
   - `GEMINI_MODEL`, `INITIAL_BALANCE` — overrides
4. **Actions** tab → enable workflows if prompted.
5. Open **Agent cron** → **Run workflow** (manual test). Leave **force** unchecked for market-hours behavior, or check it to force a cycle now.
6. After a successful run, confirm branch **`agent-data`** exists with `data/portfolio.json`, `equity.jsonl`, `reports.jsonl`, etc.

### Schedule

- Cron: every **15 minutes**, Mon–Fri, **13:00–20:59 UTC** (covers US regular hours across EST/EDT).
- Scheduled runs call `run_cycle.py` **without** `--force`, so outside the exact NY session the job exits cleanly as a skip.
- Manual **workflow_dispatch** can pass `--force`.

### Caveats

- Uses GitHub Actions minutes (public repos are free; private repos have monthly limits).
- Not a live Flask server — no APScheduler on the runner; each job is one cycle.
- First run creates the $50k book if no ledger exists yet on `agent-data`.
- Local UI and Actions ledgers are **separate** unless you sync `agent-data` into your local `sp500-backend/data/` yourself.
- Screening the S&P 500 can take a few minutes per job.
