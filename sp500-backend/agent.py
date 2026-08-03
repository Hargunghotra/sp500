"""Autonomous OpenAI paper-trading agent."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from analyzer import analyze_ticker
from config import (
    AGENT_WATCHLIST,
    ALLOW_AFTER_HOURS,
    MAX_CASH_PCT_PER_BUY,
    MAX_OPEN_TICKERS,
    MIN_CONFIDENCE,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from ledger import execute_trade, load_portfolio
from reports import append_report

logger = logging.getLogger(__name__)

_status: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "last_run": None,
    "last_error": None,
    "last_cycle_summary": None,
    "watchlist": AGENT_WATCHLIST,
}


def get_status() -> dict[str, Any]:
    return {
        **_status,
        "watchlist": list(AGENT_WATCHLIST),
        "model": OPENAI_MODEL,
        "has_api_key": bool(OPENAI_API_KEY),
        "min_confidence": MIN_CONFIDENCE,
        "max_cash_pct_per_buy": MAX_CASH_PCT_PER_BUY,
        "max_open_tickers": MAX_OPEN_TICKERS,
        "allow_after_hours": ALLOW_AFTER_HOURS,
    }


def set_enabled(enabled: bool) -> None:
    _status["enabled"] = enabled


def is_us_regular_session(now: datetime | None = None) -> bool:
    """True during Mon–Fri 09:30–16:00 America/New_York."""
    et = ZoneInfo("America/New_York")
    now = now.astimezone(et) if now else datetime.now(et)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("Model response did not contain JSON")
        return json.loads(match.group(0))


def _decide_with_openai(
    analysis: dict[str, Any],
    portfolio: dict[str, Any],
) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    owned = int(portfolio.get("positions", {}).get(analysis["ticker"], 0) or 0)
    open_tickers = len(portfolio.get("positions", {}))

    compact = {
        "ticker": analysis["ticker"],
        "current_price": analysis["current_price"],
        "sma50": analysis["sma50"],
        "trend": analysis["trend"],
        "score": analysis["score"],
        "pattern": analysis["pattern"],
        "sentiment": analysis["sentiment"],
        "supportLevel": analysis["supportLevel"],
        "resistanceLevel": analysis["resistanceLevel"],
        "recent_closes": analysis.get("recent_closes", []),
        "news_headlines": [
            {"title": n["title"], "sentiment": n["sentiment"]}
            for n in analysis.get("news", [])[:5]
        ],
        "portfolio": {
            "balance": portfolio.get("balance"),
            "owned_shares": owned,
            "open_tickers": open_tickers,
            "positions": portfolio.get("positions", {}),
        },
        "risk_rules": {
            "max_cash_pct_per_buy": MAX_CASH_PCT_PER_BUY,
            "max_open_tickers": MAX_OPEN_TICKERS,
            "min_confidence": MIN_CONFIDENCE,
        },
    }

    system = (
        "You are a conservative paper-trading assistant for US equities. "
        "Decide BUY, SELL, or HOLD for one ticker. Prefer HOLD unless the edge is clear. "
        "Respect risk rules. Respond with ONLY valid JSON matching: "
        '{"action":"BUY"|"SELL"|"HOLD","shares":number,"confidence":0-1,"reasoning":"string"}'
    )
    user = (
        "Given this market snapshot and portfolio, choose an action.\n"
        f"{json.dumps(compact, indent=2)}"
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    decision = _extract_json(content)

    action = str(decision.get("action", "HOLD")).upper()
    if action not in {"BUY", "SELL", "HOLD"}:
        action = "HOLD"
    shares = int(decision.get("shares") or 0)
    confidence = float(decision.get("confidence") or 0)
    reasoning = str(decision.get("reasoning") or "").strip() or "No reasoning provided."

    return {
        "action": action,
        "shares": max(0, shares),
        "confidence": max(0.0, min(1.0, confidence)),
        "reasoning": reasoning,
    }


def _apply_risk_caps(
    decision: dict[str, Any],
    analysis: dict[str, Any],
    portfolio: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """Return (possibly adjusted decision, skip_reason)."""
    action = decision["action"]
    shares = decision["shares"]
    confidence = decision["confidence"]
    price = float(analysis["current_price"])
    balance = float(portfolio["balance"])
    positions = portfolio.get("positions", {})
    ticker = analysis["ticker"]
    owned = int(positions.get(ticker, 0) or 0)

    if action == "HOLD" or shares <= 0:
        return {**decision, "action": "HOLD", "shares": 0}, "HOLD or zero shares"

    if confidence < MIN_CONFIDENCE:
        return {**decision, "action": "HOLD", "shares": 0}, (
            f"Confidence {confidence:.2f} below minimum {MIN_CONFIDENCE}"
        )

    if action == "BUY":
        open_count = len(positions)
        if ticker not in positions and open_count >= MAX_OPEN_TICKERS:
            return {**decision, "action": "HOLD", "shares": 0}, (
                f"Already at max open tickers ({MAX_OPEN_TICKERS})"
            )
        max_notional = balance * MAX_CASH_PCT_PER_BUY
        max_shares = int(max_notional // price) if price > 0 else 0
        if max_shares <= 0:
            return {**decision, "action": "HOLD", "shares": 0}, "Insufficient cash for min lot"
        if shares > max_shares:
            decision = {**decision, "shares": max_shares}
            decision["reasoning"] += (
                f" (shares capped to {max_shares} by {MAX_CASH_PCT_PER_BUY:.0%} cash rule)"
            )
        return decision, None

    if action == "SELL":
        if owned <= 0:
            return {**decision, "action": "HOLD", "shares": 0}, "No position to sell"
        if shares > owned:
            decision = {**decision, "shares": owned}
            decision["reasoning"] += f" (shares capped to owned {owned})"
        return decision, None

    return {**decision, "action": "HOLD", "shares": 0}, "Unknown action"


def run_cycle(*, force: bool = False) -> dict[str, Any]:
    """Scan watchlist, decide, execute, and persist a cycle report."""
    if _status["running"]:
        return {"ok": False, "error": "Cycle already running"}

    if not force and not ALLOW_AFTER_HOURS and not is_us_regular_session():
        summary = {
            "ok": True,
            "skipped": True,
            "reason": "Outside US regular market hours",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decisions": [],
        }
        _status["last_run"] = summary["timestamp"]
        _status["last_cycle_summary"] = summary
        append_report(
            {
                "type": "cycle",
                "skipped": True,
                "reason": summary["reason"],
                "decisions": [],
            }
        )
        return summary

    _status["running"] = True
    _status["last_error"] = None
    decisions: list[dict[str, Any]] = []

    try:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to sp500-backend/.env"
            )

        portfolio = load_portfolio()

        for ticker in AGENT_WATCHLIST:
            item: dict[str, Any] = {
                "ticker": ticker,
                "action": "HOLD",
                "shares": 0,
                "confidence": 0,
                "reasoning": "",
                "executed": False,
                "trade_id": None,
                "skip_reason": None,
                "error": None,
            }
            try:
                analysis = analyze_ticker(ticker, include_series=False)
                decision = _decide_with_openai(analysis, portfolio)
                adjusted, skip_reason = _apply_risk_caps(decision, analysis, portfolio)
                item.update(
                    {
                        "action": adjusted["action"],
                        "shares": adjusted["shares"],
                        "confidence": adjusted["confidence"],
                        "reasoning": adjusted["reasoning"],
                        "price": analysis["current_price"],
                        "pattern": analysis["pattern"],
                        "skip_reason": skip_reason,
                    }
                )

                if not skip_reason and adjusted["action"] in {"BUY", "SELL"}:
                    result = execute_trade(
                        ticker,
                        adjusted["action"],
                        float(analysis["current_price"]),
                        int(adjusted["shares"]),
                        pattern=analysis["pattern"],
                        reasoning=adjusted["reasoning"],
                        confidence=adjusted["confidence"],
                        source="ai",
                    )
                    item["executed"] = True
                    item["trade_id"] = result["trade"]["id"]
                    portfolio = result["portfolio"]
            except Exception as exc:  # noqa: BLE001 — per-ticker isolation
                logger.exception("Agent failed on %s", ticker)
                item["error"] = str(exc)
                item["reasoning"] = item["reasoning"] or str(exc)

            decisions.append(item)

        summary = {
            "ok": True,
            "skipped": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "executed_count": sum(1 for d in decisions if d.get("executed")),
            "decisions": decisions,
        }
        _status["last_run"] = summary["timestamp"]
        _status["last_cycle_summary"] = summary
        append_report({"type": "cycle", **summary})
        return summary
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent cycle failed")
        _status["last_error"] = str(exc)
        _status["last_run"] = datetime.now(timezone.utc).isoformat()
        err_report = {
            "ok": False,
            "error": str(exc),
            "timestamp": _status["last_run"],
            "decisions": decisions,
        }
        append_report({"type": "cycle_error", **err_report})
        return err_report
    finally:
        _status["running"] = False
