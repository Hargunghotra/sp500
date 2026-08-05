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
STRATEGY_PREV_PATH = DATA_DIR / "strategy_prev.json"

INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "50000"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

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
FX_CRYPTO_TOP_N = int(os.getenv("FX_CRYPTO_TOP_N", "8"))

MAX_CASH_PCT_PER_BUY = float(os.getenv("MAX_CASH_PCT_PER_BUY", "0.12"))
MAX_OPEN_TICKERS = int(os.getenv("MAX_OPEN_TICKERS", "12"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.55"))
ALLOW_AFTER_HOURS = os.getenv("ALLOW_AFTER_HOURS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Daily digest email (Gmail SMTP)
DIGEST_ENABLED = os.getenv("DIGEST_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DIGEST_TO = os.getenv("DIGEST_TO", "hargung123456@gmail.com")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Email after every filled paper trade (BUY/SELL)
TRADE_ALERT_ENABLED = os.getenv("TRADE_ALERT_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

SECTOR_ETFS = [
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLY",
    "XLI",
    "XLP",
    "XLU",
    "XLB",
    "XLRE",
]

# regular | extended (default) — ALLOW_AFTER_HOURS overrides to 24x7 including weekends
_raw_session = os.getenv("TRADING_SESSION", "extended").strip().lower()
TRADING_SESSION = _raw_session if _raw_session in {"regular", "extended"} else "extended"
# Extended window: Mon–Fri 4:00 AM – 8:00 PM America/New_York
EXTENDED_SESSION_START_MIN = int(os.getenv("EXTENDED_SESSION_START_MIN", str(4 * 60)))
EXTENDED_SESSION_END_MIN = int(os.getenv("EXTENDED_SESSION_END_MIN", str(20 * 60)))
REGULAR_SESSION_START_MIN = 9 * 60 + 30
REGULAR_SESSION_END_MIN = 16 * 60

# Default SL/TP percentages by asset class when model omits levels
DEFAULT_SL_PCT = {
    "equity": 0.03,
    "forex": 0.01,
    "crypto": 0.05,
}
DEFAULT_TP_PCT = {
    "equity": 0.06,
    "forex": 0.02,
    "crypto": 0.10,
}

FOREX_UNIVERSE = [
    t.strip()
    for t in os.getenv(
        "FOREX_UNIVERSE",
        "EURUSD=X,GBPUSD=X,USDJPY=X,AUDUSD=X,USDCAD=X,USDCHF=X,NZDUSD=X,EURGBP=X",
    ).split(",")
    if t.strip()
]

CRYPTO_UNIVERSE = [
    t.strip()
    for t in os.getenv(
        "CRYPTO_UNIVERSE",
        "BTC-USD,ETH-USD,SOL-USD,XRP-USD,ADA-USD,DOGE-USD,AVAX-USD,LINK-USD",
    ).split(",")
    if t.strip()
]
