"""Persistent paper-trading ledger."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from config import INITIAL_BALANCE, PORTFOLIO_PATH

_lock = threading.Lock()


def _default_portfolio() -> dict[str, Any]:
    return {
        "balance": INITIAL_BALANCE,
        "positions": {},
        "trades": [],
    }


def load_portfolio() -> dict[str, Any]:
    with _lock:
        if not PORTFOLIO_PATH.exists():
            portfolio = _default_portfolio()
            PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
            return portfolio
        data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        data.setdefault("balance", INITIAL_BALANCE)
        data.setdefault("positions", {})
        data.setdefault("trades", [])
        return data


def save_portfolio(portfolio: dict[str, Any]) -> None:
    with _lock:
        PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")


def execute_trade(
    ticker: str,
    side: str,
    price: float,
    shares: int,
    *,
    pattern: str = "",
    reasoning: str = "",
    confidence: float | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    """Execute a paper trade. Returns updated portfolio or raises ValueError."""
    ticker = ticker.upper().strip()
    side = side.upper().strip()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    if shares <= 0:
        raise ValueError("shares must be positive")
    if price <= 0:
        raise ValueError("price must be positive")

    with _lock:
        if PORTFOLIO_PATH.exists():
            portfolio = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        else:
            portfolio = _default_portfolio()
        portfolio.setdefault("balance", INITIAL_BALANCE)
        portfolio.setdefault("positions", {})
        portfolio.setdefault("trades", [])

        cost = price * shares
        positions: dict[str, int] = {
            k: int(v) for k, v in portfolio["positions"].items()
        }
        balance = float(portfolio["balance"])

        if side == "BUY" and balance < cost:
            raise ValueError("Insufficient funds")
        if side == "SELL" and positions.get(ticker, 0) < shares:
            raise ValueError("Insufficient shares")

        if side == "BUY":
            balance -= cost
            positions[ticker] = positions.get(ticker, 0) + shares
        else:
            balance += cost
            remaining = positions.get(ticker, 0) - shares
            if remaining <= 0:
                positions.pop(ticker, None)
            else:
                positions[ticker] = remaining

        trade = {
            "id": uuid.uuid4().hex[:12],
            "ticker": ticker,
            "type": side,
            "price": round(price, 4),
            "shares": shares,
            "date": datetime.now(timezone.utc).isoformat(),
            "pattern": pattern,
            "reasoning": reasoning,
            "confidence": confidence,
            "source": source,
        }

        portfolio["balance"] = round(balance, 2)
        portfolio["positions"] = positions
        portfolio["trades"] = [trade, *portfolio["trades"]]
        PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
        return {"portfolio": portfolio, "trade": trade}
