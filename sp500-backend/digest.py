"""Assemble post-close daily digest facts + Gemini briefing + email bodies."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import yfinance as yf

from analyzer import _news_title
from config import (
    EQUITY_PATH,
    GEMINI_MODEL,
    INITIAL_BALANCE,
    REPORTS_PATH,
    SECTOR_ETFS,
    STRATEGY_PATH,
    STRATEGY_PREV_PATH,
)
from equity import list_equity, mark_to_market
from ledger import load_portfolio

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

SECTOR_LABELS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLI": "Industrials",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
}


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        raw = str(ts).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def _et_date(dt: datetime) -> date:
    return dt.astimezone(ET).date()


def resolve_digest_date(day: str | date | None = None) -> date:
    if isinstance(day, date) and not isinstance(day, datetime):
        return day
    if isinstance(day, str) and day.strip():
        return date.fromisoformat(day.strip())
    return datetime.now(ET).date()


def _day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=ET).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=ET).astimezone(
        timezone.utc
    )
    return start, end


def _trades_for_day(portfolio: dict[str, Any], day: date) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    for trade in portfolio.get("trades") or []:
        dt = _parse_iso(trade.get("date"))
        if dt is None:
            continue
        if _et_date(dt) == day:
            trades.append(trade)
    trades.sort(key=lambda t: str(t.get("date") or ""))
    return trades


def _equity_bookends(day: date) -> dict[str, Any]:
    start, end = _day_bounds_utc(day)
    rows = list_equity(limit=5000)
    in_day = []
    before: dict[str, Any] | None = None
    for row in rows:
        dt = _parse_iso(row.get("timestamp"))
        if dt is None:
            continue
        if dt < start:
            before = row
        elif start <= dt < end:
            in_day.append(row)

    equity_start = None
    equity_end = None
    if in_day:
        equity_start = float(in_day[0].get("equity") or 0)
        equity_end = float(in_day[-1].get("equity") or 0)
    elif before is not None:
        equity_start = float(before.get("equity") or 0)
        equity_end = equity_start
    return {
        "equity_start": equity_start,
        "equity_end": equity_end,
        "snapshots_in_day": len(in_day),
        "day_change": (
            round(equity_end - equity_start, 2)
            if equity_start is not None and equity_end is not None
            else None
        ),
        "day_change_pct": (
            round(((equity_end / equity_start) - 1.0) * 100, 2)
            if equity_start and equity_end is not None
            else None
        ),
    }


def _load_json(path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _strategy_diff(
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    if not current and not previous:
        return {"changed": False, "summary": "No strategy on file yet."}
    if not previous and current:
        return {
            "changed": True,
            "summary": "First strategy snapshot (no previous digest baseline).",
            "current": current,
            "previous": None,
        }
    if previous and not current:
        return {
            "changed": True,
            "summary": "Strategy file missing; previous digest baseline retained.",
            "current": None,
            "previous": previous,
        }

    assert current is not None and previous is not None
    keys = ("thesis", "preferred_sectors", "styles", "risk_posture")
    changed_fields = [
        k for k in keys if json.dumps(current.get(k), sort_keys=True) != json.dumps(previous.get(k), sort_keys=True)
    ]
    if not changed_fields:
        return {
            "changed": False,
            "summary": "Strategy unchanged vs last emailed snapshot.",
            "current": current,
            "previous": previous,
            "changed_fields": [],
        }
    return {
        "changed": True,
        "summary": f"Strategy fields changed: {', '.join(changed_fields)}.",
        "current": current,
        "previous": previous,
        "changed_fields": changed_fields,
    }


def _reports_for_day(day: date) -> list[dict[str, Any]]:
    if not REPORTS_PATH.exists():
        return []
    start, end = _day_bounds_utc(day)
    out: list[dict[str, Any]] = []
    for line in REPORTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        dt = _parse_iso(row.get("timestamp"))
        if dt is None or not (start <= dt < end):
            continue
        # Compact cycle noise for the digest payload
        compact = {
            "type": row.get("type"),
            "timestamp": row.get("timestamp"),
            "ok": row.get("ok"),
            "skipped": row.get("skipped"),
            "reason": row.get("reason"),
            "error": row.get("error"),
            "executed_count": row.get("executed_count"),
            "auto_exits": row.get("auto_exits"),
        }
        decisions = row.get("decisions") or []
        if isinstance(decisions, list):
            compact["executed"] = [
                {
                    "ticker": d.get("ticker"),
                    "action": d.get("action"),
                    "shares": d.get("shares"),
                    "source": d.get("source"),
                }
                for d in decisions
                if d.get("executed")
            ]
            compact["errors"] = [
                {"ticker": d.get("ticker"), "error": d.get("error")}
                for d in decisions
                if d.get("error")
            ]
            compact["skipped_decisions"] = sum(
                1 for d in decisions if d.get("skip_reason") and not d.get("executed")
            )
        ai = row.get("ai_report") or {}
        if isinstance(ai, dict) and ai.get("headline"):
            compact["ai_headline"] = ai.get("headline")
        out.append(compact)
    return out


def _sector_overview() -> list[dict[str, Any]]:
    overview: list[dict[str, Any]] = []
    for ticker in SECTOR_ETFS:
        entry: dict[str, Any] = {
            "ticker": ticker,
            "sector": SECTOR_LABELS.get(ticker, ticker),
            "day_change_pct": None,
            "last_price": None,
            "headlines": [],
            "error": None,
        }
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="5d")
            if hist is not None and not hist.empty and len(hist) >= 2:
                prev = float(hist["Close"].iloc[-2])
                last = float(hist["Close"].iloc[-1])
                entry["last_price"] = round(last, 4)
                if prev:
                    entry["day_change_pct"] = round(((last / prev) - 1.0) * 100, 2)
            elif hist is not None and not hist.empty:
                last = float(hist["Close"].iloc[-1])
                entry["last_price"] = round(last, 4)

            headlines: list[str] = []
            for n in (yf_ticker.news or [])[:4]:
                title = _news_title(n)
                if title:
                    headlines.append(title)
            entry["headlines"] = headlines[:3]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sector overview failed for %s: %s", ticker, exc)
            entry["error"] = str(exc)
        overview.append(entry)
    return overview


def gather_digest(day: date | str | None = None) -> dict[str, Any]:
    """Collect ledger / market facts for an America/New_York calendar day."""
    digest_day = resolve_digest_date(day)
    portfolio = load_portfolio()
    mtm = mark_to_market(portfolio)
    trades = _trades_for_day(portfolio, digest_day)
    equity = _equity_bookends(digest_day)
    strategy = _load_json(STRATEGY_PATH)
    strategy_prev = _load_json(STRATEGY_PREV_PATH)
    strategy_change = _strategy_diff(strategy, strategy_prev)
    reports = _reports_for_day(digest_day)
    sectors = _sector_overview()

    cycle_ok = sum(1 for r in reports if r.get("ok") and not r.get("skipped"))
    cycle_skip = sum(1 for r in reports if r.get("skipped"))
    cycle_err = sum(1 for r in reports if r.get("ok") is False or r.get("error"))
    executed_trades = sum(len(r.get("executed") or []) for r in reports)

    return {
        "date": digest_day.isoformat(),
        "timezone": "America/New_York",
        "starting_capital": INITIAL_BALANCE,
        "equity": equity,
        "mark_to_market": {
            "equity": mtm.get("equity"),
            "cash": mtm.get("cash"),
            "positions_value": mtm.get("positions_value"),
            "unrealized_pnl": mtm.get("unrealized_pnl"),
            "realized_pnl": mtm.get("realized_pnl"),
            "total_pnl": mtm.get("total_pnl"),
            "open_positions": mtm.get("position_rows") or [],
        },
        "trades": trades,
        "trade_count": len(trades),
        "strategy": strategy,
        "strategy_change": strategy_change,
        "cycle_reports": reports,
        "cycle_stats": {
            "reports": len(reports),
            "ok": cycle_ok,
            "skipped": cycle_skip,
            "errors": cycle_err,
            "executed_from_reports": executed_trades,
        },
        "sectors": sectors,
        "model": GEMINI_MODEL,
    }


def _fallback_briefing(facts: dict[str, Any]) -> dict[str, Any]:
    equity = facts.get("equity") or {}
    mtm = facts.get("mark_to_market") or {}
    trades = facts.get("trades") or []
    change = equity.get("day_change")
    change_pct = equity.get("day_change_pct")
    pnl_blurb = (
        f"Day equity change ${change:,.2f} ({change_pct:+.2f}%)"
        if change is not None and change_pct is not None
        else f"Book equity ${float(mtm.get('equity') or 0):,.2f}"
    )
    trade_bits = [
        f"{t.get('type')} {t.get('shares')} {t.get('ticker')}" for t in trades[:8]
    ]
    sectors = facts.get("sectors") or []
    sector_lines = []
    for s in sectors:
        pct = s.get("day_change_pct")
        if pct is None:
            continue
        sector_lines.append(f"{s.get('sector')} ({s.get('ticker')}): {pct:+.2f}%")
    strat = (facts.get("strategy_change") or {}).get("summary") or "No strategy update."
    errs = (facts.get("cycle_stats") or {}).get("errors") or 0
    return {
        "headline": f"Daily desk digest - {facts.get('date')}",
        "pnl_blurb": pnl_blurb,
        "market_overview_by_sector": (
            "; ".join(sector_lines[:6])
            if sector_lines
            else "Sector ETF data unavailable."
        ),
        "trades_summary": (
            "; ".join(trade_bits) if trade_bits else "No paper trades on this ET day."
        ),
        "strategy_update": strat,
        "what_didnt_work": (
            f"{errs} cycle error report(s); review skipped/failed decisions."
            if errs
            else "No hard cycle failures recorded; watch underperformers vs thesis."
        ),
        "lesson_learned": (
            "Local fallback briefing (Gemini unavailable). "
            "Cut weak names and redeploy into highest-edge setups next session."
        ),
        "next_steps": (
            "Press winners toward TP, exit thesis breaks, keep SL/TP on every long."
        ),
        "model": GEMINI_MODEL,
        "fallback": True,
    }


def generate_briefing(facts: dict[str, Any]) -> dict[str, Any]:
    """Ask Gemini for a structured daily briefing, with local fallback."""
    from agent import _generate_content_with_retry

    schema = {
        "type": "object",
        "properties": {
            "headline": {"type": "string"},
            "pnl_blurb": {"type": "string"},
            "market_overview_by_sector": {"type": "string"},
            "trades_summary": {"type": "string"},
            "strategy_update": {"type": "string"},
            "what_didnt_work": {"type": "string"},
            "lesson_learned": {"type": "string"},
            "next_steps": {"type": "string"},
        },
        "required": [
            "headline",
            "pnl_blurb",
            "market_overview_by_sector",
            "trades_summary",
            "strategy_update",
            "what_didnt_work",
            "lesson_learned",
            "next_steps",
        ],
    }
    system = (
        "You write a post-close daily briefing for a long-only multi-asset paper desk. "
        "Ground every claim in the provided sector ETF moves, headlines, trades, "
        "MTM, strategy diff, and cycle reports. Be direct and actionable. "
        "Primary goal of the desk is maximizing paper equity; call out dead weight "
        "and missed rotations. Do not invent tickers or prices."
    )
    user = (
        "Produce the daily digest briefing JSON from these facts:\n"
        f"{json.dumps(facts, indent=2, default=str)}"
    )
    try:
        raw = _generate_content_with_retry(
            contents=user,
            system=system,
            response_schema=schema,
            temperature=0.3,
        )
        return {
            "headline": str(raw.get("headline") or "").strip()
            or f"Daily desk digest - {facts.get('date')}",
            "pnl_blurb": str(raw.get("pnl_blurb") or "").strip(),
            "market_overview_by_sector": str(
                raw.get("market_overview_by_sector") or ""
            ).strip(),
            "trades_summary": str(raw.get("trades_summary") or "").strip(),
            "strategy_update": str(raw.get("strategy_update") or "").strip(),
            "what_didnt_work": str(raw.get("what_didnt_work") or "").strip(),
            "lesson_learned": str(raw.get("lesson_learned") or "").strip(),
            "next_steps": str(raw.get("next_steps") or "").strip(),
            "model": GEMINI_MODEL,
            "fallback": False,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini digest briefing failed")
        briefing = _fallback_briefing(facts)
        briefing["error"] = str(exc)
        return briefing


def _esc(text: Any) -> str:
    s = str(text or "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_email(
    facts: dict[str, Any],
    briefing: dict[str, Any],
) -> tuple[str, str, str]:
    """Return (subject, plain_text, html)."""
    day = facts.get("date")
    headline = briefing.get("headline") or f"Daily digest {day}"
    subject = f"[SP500 Desk] {day} - {headline}"[:180]

    mtm = facts.get("mark_to_market") or {}
    equity = facts.get("equity") or {}
    trades = facts.get("trades") or []
    positions = mtm.get("open_positions") or []
    sectors = facts.get("sectors") or []
    stats = facts.get("cycle_stats") or {}

    lines = [
        f"SP500 Simulator - Daily Digest ({day} ET)",
        "=" * 48,
        briefing.get("headline") or "",
        briefing.get("pnl_blurb") or "",
        "",
        "EQUITY",
        f"  Start: {equity.get('equity_start')}",
        f"  End:   {equity.get('equity_end')}",
        f"  Change:{equity.get('day_change')} ({equity.get('day_change_pct')}%)",
        f"  MTM:   equity={mtm.get('equity')} cash={mtm.get('cash')} "
        f"unrealized={mtm.get('unrealized_pnl')} realized={mtm.get('realized_pnl')}",
        "",
        "MARKET BY SECTOR",
        briefing.get("market_overview_by_sector") or "",
    ]
    for s in sectors:
        pct = s.get("day_change_pct")
        pct_s = f"{pct:+.2f}%" if pct is not None else "n/a"
        lines.append(f"  {s.get('ticker')} {s.get('sector')}: {pct_s}")
        for h in s.get("headlines") or []:
            lines.append(f"    - {h}")

    lines.extend(
        [
            "",
            "TRADES",
            briefing.get("trades_summary") or "",
        ]
    )
    for t in trades:
        lines.append(
            f"  {t.get('date')} {t.get('type')} {t.get('shares')} {t.get('ticker')} "
            f"@ {t.get('price')} ({t.get('source')})"
        )
    if not trades:
        lines.append("  (none)")

    lines.extend(
        [
            "",
            "OPEN POSITIONS",
        ]
    )
    for p in positions:
        lines.append(
            f"  {p.get('symbol')} qty={p.get('quantity')} last={p.get('last_price')} "
            f"uPnL={p.get('unrealized_pnl')} SL={p.get('stop_loss')} TP={p.get('take_profit')}"
        )
    if not positions:
        lines.append("  (flat)")

    lines.extend(
        [
            "",
            "STRATEGY",
            briefing.get("strategy_update") or "",
            f"  Diff: {(facts.get('strategy_change') or {}).get('summary')}",
            "",
            "WHAT DIDN'T WORK",
            briefing.get("what_didnt_work") or "",
            "",
            "LESSON",
            briefing.get("lesson_learned") or "",
            "",
            "NEXT STEPS",
            briefing.get("next_steps") or "",
            "",
            "CYCLE STATS",
            f"  reports={stats.get('reports')} ok={stats.get('ok')} "
            f"skipped={stats.get('skipped')} errors={stats.get('errors')}",
        ]
    )
    text_body = "\n".join(lines)

    sector_rows = "".join(
        (
            "<tr>"
            f"<td>{_esc(s.get('ticker'))}</td>"
            f"<td>{_esc(s.get('sector'))}</td>"
            f"<td>{_esc(s.get('day_change_pct') if s.get('day_change_pct') is not None else 'n/a')}</td>"
            f"<td>{_esc('; '.join(s.get('headlines') or []))}</td>"
            "</tr>"
        )
        for s in sectors
    )
    trade_rows = "".join(
        (
            "<tr>"
            f"<td>{_esc(t.get('date'))}</td>"
            f"<td>{_esc(t.get('type'))}</td>"
            f"<td>{_esc(t.get('ticker'))}</td>"
            f"<td>{_esc(t.get('shares'))}</td>"
            f"<td>{_esc(t.get('price'))}</td>"
            f"<td>{_esc(t.get('source'))}</td>"
            "</tr>"
        )
        for t in trades
    ) or "<tr><td colspan='6'>(none)</td></tr>"
    pos_rows = "".join(
        (
            "<tr>"
            f"<td>{_esc(p.get('symbol'))}</td>"
            f"<td>{_esc(p.get('quantity'))}</td>"
            f"<td>{_esc(p.get('last_price'))}</td>"
            f"<td>{_esc(p.get('unrealized_pnl'))}</td>"
            f"<td>{_esc(p.get('stop_loss'))}</td>"
            f"<td>{_esc(p.get('take_profit'))}</td>"
            "</tr>"
        )
        for p in positions
    ) or "<tr><td colspan='6'>(flat)</td></tr>"

    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a; line-height: 1.45; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
  h2 {{ font-size: 1.05rem; margin-top: 1.4rem; border-bottom: 1px solid #ccc; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #f3f3f3; }}
  .muted {{ color: #555; }}
</style></head><body>
<h1>{_esc(briefing.get('headline'))}</h1>
<p class="muted">{_esc(day)} ET · {_esc(briefing.get('pnl_blurb'))}</p>

<h2>Market by sector</h2>
<p>{_esc(briefing.get('market_overview_by_sector'))}</p>
<table><thead><tr><th>ETF</th><th>Sector</th><th>Day %</th><th>Headlines</th></tr></thead>
<tbody>{sector_rows}</tbody></table>

<h2>Trades</h2>
<p>{_esc(briefing.get('trades_summary'))}</p>
<table><thead><tr><th>When</th><th>Side</th><th>Ticker</th><th>Qty</th><th>Price</th><th>Source</th></tr></thead>
<tbody>{trade_rows}</tbody></table>

<h2>Open positions (MTM)</h2>
<p>Equity ${_esc(mtm.get('equity'))} · Cash ${_esc(mtm.get('cash'))} ·
Unrealized ${_esc(mtm.get('unrealized_pnl'))} · Realized ${_esc(mtm.get('realized_pnl'))}</p>
<table><thead><tr><th>Symbol</th><th>Qty</th><th>Last</th><th>uPnL</th><th>SL</th><th>TP</th></tr></thead>
<tbody>{pos_rows}</tbody></table>

<h2>Strategy</h2>
<p>{_esc(briefing.get('strategy_update'))}</p>
<p class="muted">{_esc((facts.get('strategy_change') or {}).get('summary'))}</p>

<h2>What didn't work</h2>
<p>{_esc(briefing.get('what_didnt_work'))}</p>

<h2>Lesson learned</h2>
<p>{_esc(briefing.get('lesson_learned'))}</p>

<h2>Next steps</h2>
<p>{_esc(briefing.get('next_steps'))}</p>

<p class="muted">Cycles: reports={_esc(stats.get('reports'))}
 ok={_esc(stats.get('ok'))}
 skipped={_esc(stats.get('skipped'))}

 errors={_esc(stats.get('errors'))}</p>
</body></html>"""

    return subject, text_body, html_body


def persist_strategy_snapshot(strategy: dict[str, Any] | None = None) -> None:
    """Save current strategy as the baseline for the next digest diff."""
    payload = strategy if strategy is not None else _load_json(STRATEGY_PATH)
    if payload is None:
        return
    STRATEGY_PREV_PATH.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_PREV_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_digest(
    *,
    day: str | date | None = None,
    dry_run: bool = False,
    skip_gemini: bool = False,
) -> dict[str, Any]:
    """Full digest pipeline: gather → brief → email (unless dry_run)."""
    from config import DIGEST_ENABLED, DIGEST_TO
    from emailer import send_email

    facts = gather_digest(day)
    if skip_gemini:
        briefing = _fallback_briefing(facts)
    else:
        briefing = generate_briefing(facts)
    subject, text_body, html_body = format_email(facts, briefing)

    result: dict[str, Any] = {
        "ok": True,
        "date": facts["date"],
        "dry_run": dry_run,
        "subject": subject,
        "briefing": briefing,
        "facts_summary": {
            "trade_count": facts.get("trade_count"),
            "equity": facts.get("equity"),
            "cycle_stats": facts.get("cycle_stats"),
            "strategy_changed": (facts.get("strategy_change") or {}).get("changed"),
            "open_positions": len(
                (facts.get("mark_to_market") or {}).get("open_positions") or []
            ),
        },
        "to": DIGEST_TO,
    }

    if dry_run:
        result["text_preview"] = text_body[:2000]
        result["emailed"] = False
        return result

    if not DIGEST_ENABLED:
        result["ok"] = False
        result["error"] = "DIGEST_ENABLED is false"
        result["emailed"] = False
        return result

    send_result = send_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    persist_strategy_snapshot(facts.get("strategy"))
    result["emailed"] = True
    result["send"] = send_result
    return result
