"""Persistent paper-trading ledger with rich positions (avg / SL / TP)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from assets import asset_class_for, normalize_symbol
from config import (
    DEFAULT_SL_PCT,
    DEFAULT_TP_PCT,
    INITIAL_BALANCE,
    PORTFOLIO_PATH,
    REPORTS_PATH,
    STRATEGY_PATH,
)

_lock = threading.Lock()


def _default_portfolio() -> dict[str, Any]:
    return {
        "balance": INITIAL_BALANCE,
        "positions": {},
        "trades": [],
        "realized_pnl": 0.0,
    }


def _is_legacy_qty(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _migrate_positions(
    raw_positions: dict[str, Any],
    trades: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Upgrade {ticker: shares} → rich position objects."""
    migrated: dict[str, dict[str, Any]] = {}
    for key, value in (raw_positions or {}).items():
        symbol = normalize_symbol(str(key))
        if isinstance(value, dict) and "quantity" in value:
            pos = dict(value)
            pos["symbol"] = normalize_symbol(str(pos.get("symbol") or symbol))
            pos["asset_class"] = pos.get("asset_class") or asset_class_for(pos["symbol"])
            pos["side"] = pos.get("side") or "LONG"
            pos["quantity"] = float(pos.get("quantity") or 0)
            pos["avg_price"] = float(pos.get("avg_price") or 0)
            pos["stop_loss"] = pos.get("stop_loss")
            pos["take_profit"] = pos.get("take_profit")
            pos["opened_at"] = pos.get("opened_at") or datetime.now(timezone.utc).isoformat()
            avg = float(pos.get("avg_price") or 0)
            if avg > 0 and (pos["stop_loss"] is None or pos["take_profit"] is None):
                d_sl, d_tp = _default_stops(pos["asset_class"], avg)
                if pos["stop_loss"] is None:
                    pos["stop_loss"] = d_sl
                if pos["take_profit"] is None:
                    pos["take_profit"] = d_tp
            if pos["quantity"] > 0:
                migrated[pos["symbol"]] = pos
            continue
        if _is_legacy_qty(value):
            qty = float(value)
            if qty <= 0:
                continue
            avg = None
            for t in trades:
                if (
                    normalize_symbol(str(t.get("ticker") or "")) == symbol
                    and str(t.get("type") or "").upper() == "BUY"
                ):
                    avg = float(t.get("price") or 0)
                    break
            avg_f = float(avg or 0)
            cls = asset_class_for(symbol)
            sl, tp = (None, None)
            if avg_f > 0:
                sl, tp = _default_stops(cls, avg_f)
            migrated[symbol] = {
                "symbol": symbol,
                "asset_class": cls,
                "side": "LONG",
                "quantity": qty,
                "avg_price": avg_f,
                "stop_loss": sl,
                "take_profit": tp,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }
    return migrated


def _default_stops(asset_class: str, price: float) -> tuple[float, float]:
    sl_pct = DEFAULT_SL_PCT.get(asset_class, 0.03)
    tp_pct = DEFAULT_TP_PCT.get(asset_class, 0.06)
    return round(price * (1 - sl_pct), 6), round(price * (1 + tp_pct), 6)


def load_portfolio() -> dict[str, Any]:
    with _lock:
        if not PORTFOLIO_PATH.exists():
            portfolio = _default_portfolio()
            PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
            return portfolio
        data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        data.setdefault("balance", INITIAL_BALANCE)
        data.setdefault("trades", [])
        data.setdefault("realized_pnl", 0.0)
        raw = data.get("positions") or {}
        # Detect legacy qty map or missing SL/TP on rich positions
        needs_migrate = any(_is_legacy_qty(v) for v in raw.values()) or any(
            isinstance(v, dict)
            and "quantity" in v
            and (v.get("stop_loss") is None or v.get("take_profit") is None)
            for v in raw.values()
        )
        data["positions"] = _migrate_positions(raw, data.get("trades") or [])
        if needs_migrate:
            PORTFOLIO_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def save_portfolio(portfolio: dict[str, Any]) -> None:
    with _lock:
        PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")


def get_position_qty(portfolio: dict[str, Any], symbol: str) -> float:
    pos = (portfolio.get("positions") or {}).get(normalize_symbol(symbol))
    if not pos:
        return 0.0
    if _is_legacy_qty(pos):
        return float(pos)
    return float(pos.get("quantity") or 0)


def reset_portfolio() -> dict[str, Any]:
    from equity import append_equity_snapshot, clear_equity

    portfolio = _default_portfolio()
    with _lock:
        PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
        if REPORTS_PATH.exists():
            REPORTS_PATH.write_text("", encoding="utf-8")
        if STRATEGY_PATH.exists():
            STRATEGY_PATH.unlink()
    clear_equity()
    append_equity_snapshot(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equity": INITIAL_BALANCE,
            "cash": INITIAL_BALANCE,
            "positions_value": 0.0,
            "unrealized_pnl": 0.0,
            "positions": {},
        }
    )
    return portfolio


def update_position_levels(
    symbol: str,
    *,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    with _lock:
        portfolio = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8")) if PORTFOLIO_PATH.exists() else _default_portfolio()
        portfolio["positions"] = _migrate_positions(
            portfolio.get("positions") or {}, portfolio.get("trades") or []
        )
        pos = portfolio["positions"].get(symbol)
        if not pos:
            raise ValueError(f"No open position for {symbol}")
        if stop_loss is not None:
            pos["stop_loss"] = float(stop_loss)
        if take_profit is not None:
            pos["take_profit"] = float(take_profit)
        portfolio["positions"][symbol] = pos
        PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
        return portfolio


def execute_trade(
    ticker: str,
    side: str,
    price: float,
    shares: float,
    *,
    pattern: str = "",
    reasoning: str = "",
    confidence: float | None = None,
    source: str = "manual",
    stop_loss: float | None = None,
    take_profit: float | None = None,
    asset_class: str | None = None,
) -> dict[str, Any]:
    """Execute a paper trade against rich positions."""
    from equity import append_equity_snapshot, mark_to_market

    ticker = normalize_symbol(ticker)
    side = side.upper().strip()
    shares = float(shares)
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    if shares <= 0:
        raise ValueError("shares must be positive")
    if price <= 0:
        raise ValueError("price must be positive")

    cls = asset_class or asset_class_for(ticker)

    with _lock:
        if PORTFOLIO_PATH.exists():
            portfolio = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        else:
            portfolio = _default_portfolio()
        portfolio.setdefault("balance", INITIAL_BALANCE)
        portfolio.setdefault("trades", [])
        portfolio.setdefault("realized_pnl", 0.0)
        portfolio["positions"] = _migrate_positions(
            portfolio.get("positions") or {}, portfolio.get("trades") or []
        )

        positions: dict[str, dict[str, Any]] = portfolio["positions"]
        balance = float(portfolio["balance"])
        cost = price * shares

        if side == "BUY" and balance < cost:
            raise ValueError("Insufficient funds")
        owned = float((positions.get(ticker) or {}).get("quantity") or 0)
        if side == "SELL" and owned < shares - 1e-9:
            raise ValueError("Insufficient shares")

        realized_delta = 0.0
        if side == "BUY":
            balance -= cost
            existing = positions.get(ticker)
            if existing:
                old_qty = float(existing["quantity"])
                old_avg = float(existing["avg_price"] or price)
                new_qty = old_qty + shares
                new_avg = ((old_avg * old_qty) + (price * shares)) / new_qty
                existing["quantity"] = new_qty
                existing["avg_price"] = round(new_avg, 6)
                if stop_loss is not None:
                    existing["stop_loss"] = float(stop_loss)
                if take_profit is not None:
                    existing["take_profit"] = float(take_profit)
                positions[ticker] = existing
            else:
                sl, tp = stop_loss, take_profit
                if sl is None or tp is None:
                    d_sl, d_tp = _default_stops(cls, price)
                    sl = float(sl if sl is not None else d_sl)
                    tp = float(tp if tp is not None else d_tp)
                positions[ticker] = {
                    "symbol": ticker,
                    "asset_class": cls,
                    "side": "LONG",
                    "quantity": shares,
                    "avg_price": round(price, 6),
                    "stop_loss": sl,
                    "take_profit": tp,
                    "opened_at": datetime.now(timezone.utc).isoformat(),
                }
        else:
            existing = positions[ticker]
            avg = float(existing.get("avg_price") or price)
            realized_delta = (price - avg) * shares
            portfolio["realized_pnl"] = round(
                float(portfolio.get("realized_pnl") or 0) + realized_delta, 2
            )
            balance += cost
            remaining = float(existing["quantity"]) - shares
            if remaining <= 1e-9:
                positions.pop(ticker, None)
            else:
                existing["quantity"] = remaining
                positions[ticker] = existing

        trade = {
            "id": uuid.uuid4().hex[:12],
            "ticker": ticker,
            "type": side,
            "price": round(price, 6),
            "shares": shares,
            "date": datetime.now(timezone.utc).isoformat(),
            "pattern": pattern,
            "reasoning": reasoning,
            "confidence": confidence,
            "source": source,
            "asset_class": cls,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "realized_pnl": round(realized_delta, 2) if side == "SELL" else None,
        }

        portfolio["balance"] = round(balance, 2)
        portfolio["positions"] = positions
        portfolio["trades"] = [trade, *portfolio["trades"]]
        PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")

    snapshot = mark_to_market(portfolio)
    append_equity_snapshot(snapshot)
    try:
        from emailer import send_trade_alert

        send_trade_alert(trade, equity=snapshot)
    except Exception:  # noqa: BLE001
        # Never block fills on email issues
        pass
    return {"portfolio": portfolio, "trade": trade, "equity": snapshot}
