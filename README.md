# S&P 500 Trading Simulator

Decoupled Next.js + Flask autonomous paper desk with a glassy TradingView-inspired UI, S&P 500 screening, Gemini strategy, and portfolio equity tracking.

## Setup (local)

1. Copy `sp500-backend/.env.example` → `sp500-backend/.env` and set `GEMINI_API_KEY`.
2. Optional digest email: set `SMTP_USER`, `SMTP_PASSWORD` (Gmail App Password), `DIGEST_TO`.
3. `pip install -r sp500-backend/requirements.txt`

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

One-shot cycle / digest (same as Actions):

```bash
cd sp500-backend
python run_cycle.py          # respects US market hours
python run_cycle.py --force  # run anytime
python run_daily_digest.py --dry-run --skip-gemini   # preview email body
python run_daily_digest.py                           # send via Gmail SMTP
```

## Autonomy (local UI)

Each cycle:
1. Screens the S&P 500 locally (technicals + patterns; news on shortlist)
2. Asks Gemini for a **profit-max** sector/style strategy + BUY/SELL/HOLD on top candidates
3. Executes paper trades into a **$50,000** book (long-only; SL/TP required)
4. Writes equity snapshots + AI trade reports

Use **Start 24/7** / **Run once**, or **Reset book to $50,000**.

Default risk knobs (still hard-capped): `MIN_CONFIDENCE=0.55`, `MAX_CASH_PCT_PER_BUY=0.12`, `MAX_OPEN_TICKERS=12`.

## Free 24/7 without your PC

| Path | Cost | Role |
|------|------|------|
| **GitHub Actions** (default) | Free minutes | Trade cycles every 15m + daily digest email; ledger on `agent-data` |
| **Oracle Always Free VM** (optional) | Free ARM/AMD VM | True always-on cron if Actions delays or minute limits become an issue |

Prefer Actions for this repo. Oracle is the upgrade path, not required to start.

### GitHub Actions — agent cron

The workflow [`.github/workflows/agent-cron.yml`](.github/workflows/agent-cron.yml) runs the agent on GitHub-hosted runners and persists the ledger on an `agent-data` branch (ephemeral runners cannot keep local JSON otherwise).

#### Enable trade cycles

1. Push this repo to GitHub (already: `Hargunghotra/sp500`).
2. Repo **Settings → Secrets and variables → Actions → New repository secret**
   - `GEMINI_API_KEY` — Gemini API key
3. Optional **Variables**:
   - `ALLOW_AFTER_HOURS=true` — trade nights/weekends (default off; schedule still uses `force=false`)
   - `TRADING_SESSION=extended` — 4:00–20:00 ET (default)
   - `GEMINI_MODEL`, `INITIAL_BALANCE` — overrides
4. **Actions** tab → enable workflows if prompted.
5. Open **Agent cron** → **Run workflow** (manual test).
6. After a successful run, confirm branch **`agent-data`** exists with `data/portfolio.json`, `equity.jsonl`, `reports.jsonl`, etc.

#### Schedule (agent)

- Cron: every **15 minutes**, Mon–Fri, covering US **extended** hours (~4:00–20:00 ET).
- Scheduled runs call `run_cycle.py` **without** `--force`, so outside session the job exits as a skip.
- Manual **workflow_dispatch** can pass `--force`.
- GitHub may delay scheduled jobs by a few minutes; that is normal for free Actions.

### GitHub Actions — daily digest email

The workflow [`.github/workflows/daily-digest.yml`](.github/workflows/daily-digest.yml) emails a post-close briefing (trades, MTM, sector ETF/news, strategy diff, failures, lessons, next steps) after extended close (~20:20 ET).

#### Gmail App Password (one-time)

1. Google Account → **Security** → enable 2-Step Verification.
2. Create an **App Password** for Mail.
3. Repo secrets:
   - `SMTP_USER=hargung123456@gmail.com`
   - `SMTP_PASSWORD=<app password>`
   - Keep `GEMINI_API_KEY`
4. Optional variable or secret: `DIGEST_TO=hargung123456@gmail.com` (defaults to that address if unset).
5. Optional variable: `DIGEST_ENABLED=true`.
6. **Actions → Daily digest → Run workflow** once to verify inbox delivery (leave dry-run unchecked for a real send).

#### Schedule (digest)

- Cron: `20 0 * * 2-6` and `20 1 * * 2-6` UTC (covers EDT/EST ~20:20 ET after extended close).
- Restores ledger from `agent-data`, runs `python run_daily_digest.py`, then persists `data/strategy_prev.json` for strategy-change diffs.

### Oracle Always Free (optional upgrade)

If Actions flakiness or private-repo minute limits become painful:

1. Create an Oracle Cloud **Always Free** VM (ARM Ampere or eligible AMD).
2. Install Python 3.12+, clone this repo, copy `.env` with `GEMINI_API_KEY` (+ SMTP secrets if you want email from the VM).
3. Persist `sp500-backend/data/` on disk (do not rely on ephemeral storage alone).
4. Cron or systemd timer examples:

```cron
*/15 * * * 1-5  cd /opt/sp500-simulator/sp500-backend && /opt/sp500-simulator/venv/bin/python run_cycle.py
20 20 * * 1-5   cd /opt/sp500-simulator/sp500-backend && /opt/sp500-simulator/venv/bin/python run_daily_digest.py
```

(Adjust the digest minute for your VM timezone, or set `TZ=America/New_York`.)

No paid hosting is required for either path. No live brokerage automation.

### Caveats

- Uses GitHub Actions minutes (public repos are free; private repos have monthly limits).
- Not a live Flask server on the runner — each job is one cycle or one digest send.
- First run creates the $50k book if no ledger exists yet on `agent-data`.
- Local UI and Actions ledgers are **separate** unless you sync `agent-data` into your local `sp500-backend/data/` yourself.
- Screening the S&P 500 can take a few minutes per job.
