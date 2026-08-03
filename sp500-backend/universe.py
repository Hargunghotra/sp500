"""S&P 500 universe loader with Wikipedia refresh + local cache."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from config import SP500_CACHE_PATH

logger = logging.getLogger(__name__)

# Minimal seed if network/cache fail
_SEED = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B", "JPM", "V",
    "UNH", "XOM", "JNJ", "WMT", "MA", "PG", "HD", "CVX", "MRK", "ABBV",
    "COST", "PEP", "KO", "AVGO", "LLY", "TSLA", "MCD", "CSCO", "ACN", "CRM",
    "LIN", "BAC", "TMO", "ABT", "DHR", "WFC", "TXN", "DIS", "NEE", "PM",
    "ORCL", "AMD", "INTC", "QCOM", "IBM", "CAT", "GE", "BA", "SPGI", "NOW",
]


def _scrape_wikipedia() -> list[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "constituents"}) or soup.find(
        "table", {"class": "wikitable"}
    )
    if table is None:
        raise RuntimeError("S&P 500 table not found")
    tickers: list[str] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if not cells:
            continue
        sym = cells[0].get_text(strip=True).replace(".", "-").upper()
        if re.match(r"^[A-Z][A-Z0-9\-]{0,6}$", sym):
            tickers.append(sym)
    return sorted(set(tickers))


def _read_cache() -> dict[str, Any] | None:
    if not SP500_CACHE_PATH.exists():
        return None
    try:
        return json.loads(SP500_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _write_cache(tickers: list[str]) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "tickers": tickers,
    }
    SP500_CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_sp500_tickers(*, refresh: bool = False) -> list[str]:
    cached = _read_cache()
    if cached and not refresh and cached.get("tickers"):
        return [str(t).upper() for t in cached["tickers"]]

    try:
        tickers = _scrape_wikipedia()
        if len(tickers) < 100:
            raise RuntimeError(f"Unexpectedly small universe: {len(tickers)}")
        _write_cache(tickers)
        return tickers
    except Exception:  # noqa: BLE001
        logger.exception("Failed to refresh S&P 500 list")
        if cached and cached.get("tickers"):
            return [str(t).upper() for t in cached["tickers"]]
        _write_cache(_SEED)
        return list(_SEED)
