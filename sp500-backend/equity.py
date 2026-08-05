"""Portfolio equity curve persistence and mark-to-market."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

from assets import normalize_symbol
from config import EQUITY_PATH, INITIAL_BALANCE
from ledger import load_portfolio

logger = logging.getLogger(__name__)
_lock = threading.Lock()


def _latest_prices(tickers: list[str]) -> dict[str, float]:
    prices: dict[str, float] = {}
    symbols = [normalize_symbol(t) for t in tickers]
    if not symbols:
        return prices
    try:
        data = yf.download(
            tickers=" ".join(symbols),
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
        if data is None or data.empty:
            return prices
        if len(symbols) == 1:
            ticker = symbols[0]
            close = data["Close"].dropna()
            if not close.empty:
                prices[ticker] = float(close.iloc[-1])
            return prices
        for ticker in symbols:
            try:
                close = data[ticker]["Close"].dropna()
                if not close.empty:
                    prices[ticker] = float(close.iloc[-1])
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        logger.exception("Failed bulk price fetch; falling back per ticker")
        for ticker in symbols:
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
    raw_positions = portfolio.get("positions") or {}
    symbols: list[str] = []
    normalized: dict[str, dict[str, Any]] = {}

    for key, value in raw_positions.items():
        if isinstance(value, dict) and "quantity" in value:
            symbol = normalize_symbol(str(value.get("symbol") or key))
            qty = float(value.get("quantity") or 0)
            if qty <= 0:
                continue
            normalized[symbol] = {**value, "symbol": symbol, "quantity": qty}
            symbols.append(symbol)
        elif isinstance(value, (int, float)):
            symbol = normalize_symbol(str(key))
            qty = float(value)
            if qty <= 0:
                continue
            normalized[symbol] = {
                "symbol": symbol,
                "quantity": qty,
                "avg_price": 0.0,
                "side": "LONG",
                "asset_class": "equity",
                "stop_loss": None,
                "take_profit": None,
            }
            symbols.append(symbol)

    prices = _latest_prices(symbols)
    positions_value = 0.0
    unrealized = 0.0
    rows: list[dict[str, Any]] = []

    for symbol, pos in normalized.items():
        qty = float(pos["quantity"])
        avg = float(pos.get("avg_price") or 0)
        last = prices.get(symbol)
        if last is None:
            last = avg
        market_value = last * qty
        trade_value = avg * qty
        pnl = (last - avg) * qty if avg else 0.0
        pnl_pct = ((last / avg) - 1.0) * 100 if avg else 0.0
        positions_value += market_value
        unrealized += pnl
        rows.append(
            {
                "symbol": symbol,
                "asset_class": pos.get("asset_class") or "equity",
                "side": pos.get("side") or "LONG",
                "quantity": qty,
                "avg_price": round(avg, 6),
                "stop_loss": pos.get("stop_loss"),
                "take_profit": pos.get("take_profit"),
                "last_price": round(last, 6),
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "trade_value": round(trade_value, 2),
                "market_value": round(market_value, 2),
                "opened_at": pos.get("opened_at"),
            }
        )

    equity = cash + positions_value
    realized = float(portfolio.get("realized_pnl") or 0)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "equity": round(equity, 2),
        "cash": round(cash, 2),
        "positions_value": round(positions_value, 2),
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl": round(realized, 2),
        "total_pnl": round(realized + unrealized, 2),
        "starting_capital": INITIAL_BALANCE,
        "positions": {r["symbol"]: r for r in rows},
        "position_rows": rows,
    }


def append_equity_snapshot(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = snapshot or mark_to_market()
    line = json.dumps(
        {
            "timestamp": snap["timestamp"],
            "equity": snap["equity"],
            "cash": snap["cash"],
            "positions_value": snap["positions_value"],
            "unrealized_pnl": snap.get("unrealized_pnl", 0),
        },
        ensure_ascii=False,
    )
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
