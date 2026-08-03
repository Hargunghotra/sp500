"""Portfolio equity curve persistence and mark-to-market."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

from config import EQUITY_PATH
from ledger import load_portfolio

logger = logging.getLogger(__name__)
_lock = threading.Lock()


def _latest_prices(tickers: list[str]) -> dict[str, float]:
    prices: dict[str, float] = {}
    if not tickers:
        return prices
    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
        if data is None or data.empty:
            return prices
        if len(tickers) == 1:
            ticker = tickers[0]
            close = data["Close"].dropna()
            if not close.empty:
                prices[ticker] = float(close.iloc[-1])
            return prices
        for ticker in tickers:
            try:
                close = data[ticker]["Close"].dropna()
                if not close.empty:
                    prices[ticker] = float(close.iloc[-1])
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        logger.exception("Failed bulk price fetch; falling back per ticker")
        for ticker in tickers:
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if not hist.empty:
                    prices[ticker] = float(hist["Close"].iloc[-1])
            except Exception:  # noqa: BLE001
                continue
    return prices


def mark_to_market(portfolio: dict[str, Any] | None = None) -> dict[str, Any]:
    portfolio = portfolio or load_portfolio()
    cash = float(portfolio.get("balance") or 0)
    positions = {k: int(v) for k, v in (portfolio.get("positions") or {}).items()}
    prices = _latest_prices(list(positions.keys()))
    positions_value = 0.0
    lots: dict[str, dict[str, float | int]] = {}
    for ticker, shares in positions.items():
        px = prices.get(ticker)
        if px is None:
            continue
        value = px * shares
        positions_value += value
        lots[ticker] = {"shares": shares, "price": round(px, 4), "value": round(value, 2)}
    equity = cash + positions_value
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "equity": round(equity, 2),
        "cash": round(cash, 2),
        "positions_value": round(positions_value, 2),
        "positions": lots,
    }


def append_equity_snapshot(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = snapshot or mark_to_market()
    line = json.dumps(snap, ensure_ascii=False)
    with _lock:
        with EQUITY_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return snap


def list_equity(limit: int = 500) -> list[dict[str, Any]]:
    if not EQUITY_PATH.exists():
        return []
    with _lock:
        lines = EQUITY_PATH.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if limit and len(rows) > limit:
        return rows[-limit:]
    return rows


def clear_equity() -> None:
    with _lock:
        if EQUITY_PATH.exists():
            EQUITY_PATH.write_text("", encoding="utf-8")
