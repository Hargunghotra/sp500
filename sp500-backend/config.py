import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
load_dotenv(BASE_DIR / ".env")

DATA_DIR.mkdir(parents=True, exist_ok=True)

PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
REPORTS_PATH = DATA_DIR / "reports.jsonl"
EQUITY_PATH = DATA_DIR / "equity.jsonl"
SP500_CACHE_PATH = DATA_DIR / "sp500.json"
SCREEN_CACHE_PATH = DATA_DIR / "screen_cache.json"
STRATEGY_PATH = DATA_DIR / "strategy.json"

INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "50000"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Optional override; empty = full S&P 500 screen
AGENT_WATCHLIST = [
    t.strip().upper()
    for t in os.getenv("AGENT_WATCHLIST", "").split(",")
    if t.strip()
]

AGENT_INTERVAL_MINUTES = int(os.getenv("AGENT_INTERVAL_MINUTES", "15"))
AGENT_ENABLED_DEFAULT = os.getenv("AGENT_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

SCREEN_TOP_N = int(os.getenv("SCREEN_TOP_N", "25"))
SCREEN_CACHE_MINUTES = int(os.getenv("SCREEN_CACHE_MINUTES", "30"))
SCREEN_BATCH_SIZE = int(os.getenv("SCREEN_BATCH_SIZE", "40"))

# Risk guards for $50k book
MAX_CASH_PCT_PER_BUY = float(os.getenv("MAX_CASH_PCT_PER_BUY", "0.08"))
MAX_OPEN_TICKERS = int(os.getenv("MAX_OPEN_TICKERS", "10"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.65"))
ALLOW_AFTER_HOURS = os.getenv("ALLOW_AFTER_HOURS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
