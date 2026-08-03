"""Autonomous Gemini paper-trading agent over S&P 500 screen."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from config import (
    ALLOW_AFTER_HOURS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAX_CASH_PCT_PER_BUY,
    MAX_OPEN_TICKERS,
    MIN_CONFIDENCE,
    STRATEGY_PATH,
)
from equity import append_equity_snapshot, mark_to_market
from ledger import execute_trade, load_portfolio
from reports import append_report
from screener import screen_universe

logger = logging.getLogger(__name__)

_status: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "last_run": None,
    "last_error": None,
    "last_cycle_summary": None,
    "strategy": None,
    "screened_count": 0,
    "universe_size": 0,
}


def get_status() -> dict[str, Any]:
    strategy = _status.get("strategy")
    if strategy is None and STRATEGY_PATH.exists():
        try:
            strategy = json.loads(STRATEGY_PATH.read_text(encoding="utf-8"))
            _status["strategy"] = strategy
        except json.JSONDecodeError:
            strategy = None
    return {
        **_status,
        "strategy": strategy,
        "model": GEMINI_MODEL,
        "provider": "gemini",
        "has_api_key": bool(GEMINI_API_KEY),
        "min_confidence": MIN_CONFIDENCE,
        "max_cash_pct_per_buy": MAX_CASH_PCT_PER_BUY,
        "max_open_tickers": MAX_OPEN_TICKERS,
        "allow_after_hours": ALLOW_AFTER_HOURS,
    }


def set_enabled(enabled: bool) -> None:
    _status["enabled"] = enabled


def is_us_regular_session(now: datetime | None = None) -> bool:
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


def _normalize_decision(decision: dict[str, Any]) -> dict[str, Any]:
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


def _gemini_client():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to sp500-backend/.env")
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    message = str(exc)
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", message, re.IGNORECASE)
    if match:
        return min(90.0, float(match.group(1)) + 1.0)
    return min(60.0, 2 ** attempt)


def _generate_content_with_retry(
    *,
    contents: str,
    system: str,
    response_schema: dict[str, Any],
    temperature: float = 0.2,
    max_attempts: int = 4,
) -> dict[str, Any]:
    from google.genai import types

    client = _gemini_client()
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
            return _extract_json(response.text or "{}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            status = getattr(exc, "status_code", None)
            is_rate = status == 429 or "RESOURCE_EXHAUSTED" in str(exc)
            is_busy = status in {503, 500} or "UNAVAILABLE" in str(exc)
            if attempt >= max_attempts or not (is_rate or is_busy):
                raise
            delay = _retry_delay_seconds(exc, attempt)
            logger.warning(
                "Gemini attempt %s/%s failed (%s). Retrying in %.1fs",
                attempt,
                max_attempts,
                type(exc).__name__,
                delay,
            )
            time.sleep(delay)

    assert last_error is not None
    raise last_error


def _strategy_cycle_with_gemini(
    candidates: list[dict[str, Any]],
    portfolio: dict[str, Any],
    market_breadth: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """One Gemini call: strategy + decisions + ai_report."""
    compact_candidates = []
    for c in candidates:
        compact_candidates.append(
            {
                "ticker": c["ticker"],
                "current_price": c.get("current_price"),
                "sma50": c.get("sma50"),
                "trend": c.get("trend"),
                "pattern": c.get("pattern"),
                "score": c.get("score"),
                "sentiment": c.get("sentiment", "NEUTRAL"),
                "dist_to_support_pct": c.get("dist_to_support_pct"),
                "dist_to_resistance_pct": c.get("dist_to_resistance_pct"),
                "return_20d_pct": c.get("return_20d_pct"),
                "opportunity_score": c.get("opportunity_score"),
                "news_headlines": c.get("news_headlines", [])[:3],
                "owned_shares": int(
                    (portfolio.get("positions") or {}).get(c["ticker"], 0) or 0
                ),
            }
        )

    payload = {
        "portfolio": {
            "balance": portfolio.get("balance"),
            "positions": portfolio.get("positions", {}),
            "open_tickers": len(portfolio.get("positions") or {}),
        },
        "risk_rules": {
            "max_cash_pct_per_buy": MAX_CASH_PCT_PER_BUY,
            "max_open_tickers": MAX_OPEN_TICKERS,
            "min_confidence": MIN_CONFIDENCE,
        },
        "market_breadth": market_breadth,
        "candidates": compact_candidates,
    }

    system = (
        "You are an autonomous US equity paper-trading strategist. "
        "First form a portfolio strategy (preferred sectors/industries, stock styles such as "
        "momentum/quality/mean-reversion, risk posture). "
        "Use historical structure (SMA trend, support/resistance, consolidations/breakouts), "
        "proved technical patterns, and current news sentiment. "
        "Then decide BUY/SELL/HOLD for each candidate. Prefer HOLD unless edge is clear. "
        "Respect risk rules. Also write ai_report."
    )
    user = (
        "Build strategy and trade decisions for this screened S&P 500 shortlist.\n"
        f"{json.dumps(payload, indent=2)}"
    )

    schema = {
        "type": "object",
        "properties": {
            "strategy": {
                "type": "object",
                "properties": {
                    "thesis": {"type": "string"},
                    "preferred_sectors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "styles": {"type": "array", "items": {"type": "string"}},
                    "risk_posture": {"type": "string"},
                },
                "required": ["thesis", "preferred_sectors", "styles", "risk_posture"],
            },
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
                        "shares": {"type": "integer"},
                        "confidence": {"type": "number"},
                        "reasoning": {"type": "string"},
                    },
                    "required": [
                        "ticker",
                        "action",
                        "shares",
                        "confidence",
                        "reasoning",
                    ],
                },
            },
            "ai_report": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "summary": {"type": "string"},
                    "market_read": {"type": "string"},
                    "risk_notes": {"type": "string"},
                    "outlook": {"type": "string"},
                },
                "required": [
                    "headline",
                    "summary",
                    "market_read",
                    "risk_notes",
                    "outlook",
                ],
            },
        },
        "required": ["strategy", "decisions", "ai_report"],
    }

    raw = _generate_content_with_retry(
        contents=user,
        system=system,
        response_schema=schema,
        temperature=0.25,
    )

    by_ticker: dict[str, dict[str, Any]] = {}
    for item in raw.get("decisions") or []:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").upper().strip()
        if not ticker:
            continue
        by_ticker[ticker] = _normalize_decision(item)

    strategy_raw = raw.get("strategy") or {}
    strategy = {
        "thesis": str(strategy_raw.get("thesis") or "").strip(),
        "preferred_sectors": [
            str(s) for s in (strategy_raw.get("preferred_sectors") or []) if s
        ],
        "styles": [str(s) for s in (strategy_raw.get("styles") or []) if s],
        "risk_posture": str(strategy_raw.get("risk_posture") or "").strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model": GEMINI_MODEL,
    }

    report_raw = raw.get("ai_report") or {}
    ai_report = {
        "headline": str(report_raw.get("headline") or "Cycle report").strip(),
        "summary": str(report_raw.get("summary") or "").strip(),
        "market_read": str(report_raw.get("market_read") or "").strip(),
        "risk_notes": str(report_raw.get("risk_notes") or "").strip(),
        "outlook": str(report_raw.get("outlook") or "").strip(),
        "model": GEMINI_MODEL,
    }
    return by_ticker, strategy, ai_report


def _fallback_ai_report(
    decisions: list[dict[str, Any]],
    portfolio: dict[str, Any],
    *,
    error: str | None = None,
) -> dict[str, Any]:
    executed = [d for d in decisions if d.get("executed")]
    if executed:
        headline = f"Executed {len(executed)} trade(s)"
        summary = "; ".join(
            f"{d['action']} {d['shares']} {d['ticker']}" for d in executed
        )
    else:
        headline = "No trades executed this cycle"
        summary = f"Cash ${float(portfolio.get('balance') or 0):,.2f}."
    return {
        "headline": headline,
        "summary": summary,
        "market_read": "Local fallback briefing (Gemini unavailable or rate-limited).",
        "risk_notes": error or "Used deterministic summary without Gemini narrative.",
        "outlook": "Retry after the free-tier quota window resets.",
        "model": GEMINI_MODEL,
        "error": error,
    }


def _apply_risk_caps(
    decision: dict[str, Any],
    candidate: dict[str, Any],
    portfolio: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    action = decision["action"]
    shares = decision["shares"]
    confidence = decision["confidence"]
    price = float(candidate["current_price"])
    balance = float(portfolio["balance"])
    positions = portfolio.get("positions", {})
    ticker = candidate["ticker"]
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
    if _status["running"]:
        return {"ok": False, "error": "Cycle already running"}

    if not force and not ALLOW_AFTER_HOURS and not is_us_regular_session():
        summary = {
            "ok": True,
            "skipped": True,
            "reason": "Outside US regular market hours",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decisions": [],
            "ai_report": None,
            "strategy": _status.get("strategy"),
        }
        _status["last_run"] = summary["timestamp"]
        _status["last_cycle_summary"] = summary
        append_report({"type": "cycle", **summary})
        return summary

    _status["running"] = True
    _status["last_error"] = None
    decisions: list[dict[str, Any]] = []

    try:
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to sp500-backend/.env"
            )

        portfolio = load_portfolio()
        screen = screen_universe(force=force)
        candidates = screen.get("candidates") or []
        _status["screened_count"] = len(candidates)
        _status["universe_size"] = int(screen.get("universe_size") or 0)

        by_ticker: dict[str, dict[str, Any]] = {}
        strategy: dict[str, Any] | None = None
        ai_report: dict[str, Any] | None = None

        try:
            by_ticker, strategy, ai_report = _strategy_cycle_with_gemini(
                candidates,
                portfolio,
                screen.get("market_breadth") or {},
            )
            STRATEGY_PATH.write_text(json.dumps(strategy, indent=2), encoding="utf-8")
            _status["strategy"] = strategy
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini strategy cycle failed")
            for c in candidates:
                by_ticker[c["ticker"]] = {
                    "action": "HOLD",
                    "shares": 0,
                    "confidence": 0.0,
                    "reasoning": f"Gemini unavailable this cycle: {exc}",
                }
            strategy = {
                "thesis": "Fallback: hold existing risk until Gemini recovers.",
                "preferred_sectors": [],
                "styles": ["defensive"],
                "risk_posture": "risk-off",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "model": GEMINI_MODEL,
                "error": str(exc),
            }
            _status["strategy"] = strategy
            ai_report = _fallback_ai_report([], portfolio, error=str(exc))

        cand_map = {c["ticker"]: c for c in candidates}
        for ticker, candidate in cand_map.items():
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
                "price": candidate.get("current_price"),
                "pattern": candidate.get("pattern"),
            }
            try:
                decision = by_ticker.get(ticker) or {
                    "action": "HOLD",
                    "shares": 0,
                    "confidence": 0.0,
                    "reasoning": "No model decision returned for ticker.",
                }
                adjusted, skip_reason = _apply_risk_caps(decision, candidate, portfolio)
                item.update(
                    {
                        "action": adjusted["action"],
                        "shares": adjusted["shares"],
                        "confidence": adjusted["confidence"],
                        "reasoning": adjusted["reasoning"],
                        "skip_reason": skip_reason,
                    }
                )
                if not skip_reason and adjusted["action"] in {"BUY", "SELL"}:
                    result = execute_trade(
                        ticker,
                        adjusted["action"],
                        float(candidate["current_price"]),
                        int(adjusted["shares"]),
                        pattern=str(candidate.get("pattern") or ""),
                        reasoning=adjusted["reasoning"],
                        confidence=adjusted["confidence"],
                        source="ai",
                    )
                    item["executed"] = True
                    item["trade_id"] = result["trade"]["id"]
                    portfolio = result["portfolio"]
            except Exception as exc:  # noqa: BLE001
                logger.exception("Trade application failed on %s", ticker)
                item["error"] = str(exc)
                item["reasoning"] = item["reasoning"] or str(exc)
            decisions.append(item)

        if not ai_report:
            ai_report = _fallback_ai_report(decisions, portfolio)
        executed = [d for d in decisions if d.get("executed")]
        if executed:
            ai_report["summary"] = (
                (ai_report.get("summary") or "")
                + " Executed: "
                + "; ".join(
                    f"{d['action']} {d['shares']} {d['ticker']}" for d in executed
                )
            ).strip()

        # Equity snapshot even if no fills (MTM drift)
        if not executed:
            append_equity_snapshot(mark_to_market(portfolio))

        summary = {
            "ok": True,
            "skipped": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "executed_count": len(executed),
            "universe_size": _status["universe_size"],
            "screened_count": _status["screened_count"],
            "strategy": strategy,
            "decisions": decisions,
            "ai_report": ai_report,
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
            "ai_report": _fallback_ai_report(decisions, load_portfolio(), error=str(exc)),
            "strategy": _status.get("strategy"),
        }
        append_report({"type": "cycle_error", **err_report})
        return err_report
    finally:
        _status["running"] = False
