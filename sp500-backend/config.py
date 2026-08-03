import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
load_dotenv(BASE_DIR / ".env")

DATA_DIR.mkdir(parents=True, exist_ok=True)

PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
REPORTS_PATH = DATA_DIR / "reports.jsonl"

INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "100000"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

AGENT_WATCHLIST = [
    t.strip().upper()
    for t in os.getenv(
        "AGENT_WATCHLIST",
        "SPY,QQQ,AAPL,MSFT,NVDA,AMZN,META,GOOGL",
    ).split(",")
    if t.strip()
]

AGENT_INTERVAL_MINUTES = int(os.getenv("AGENT_INTERVAL_MINUTES", "15"))
AGENT_ENABLED_DEFAULT = os.getenv("AGENT_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Risk guards
MAX_CASH_PCT_PER_BUY = float(os.getenv("MAX_CASH_PCT_PER_BUY", "0.05"))
MAX_OPEN_TICKERS = int(os.getenv("MAX_OPEN_TICKERS", "3"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.65"))
ALLOW_AFTER_HOURS = os.getenv("ALLOW_AFTER_HOURS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
