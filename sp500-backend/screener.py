"""Local multi-asset screener: S&P 500 + forex + crypto shortlist."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from assets import asset_class_for, normalize_symbol
from config import (
    AGENT_WATCHLIST,
    CRYPTO_UNIVERSE,
    FOREX_UNIVERSE,
    FX_CRYPTO_TOP_N,
    SCREEN_BATCH_SIZE,
    SCREEN_CACHE_MINUTES,
    SCREEN_CACHE_PATH,
    SCREEN_TOP_N,
)
from universe import get_sp500_tickers

logger = logging.getLogger(__name__)


def _score_row(close: pd.Series) -> dict[str, Any] | None:
    if close is None or close.dropna().shape[0] < 60:
        return None
    close = close.dropna()
    current = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    high_6m = float(close.tail(126).max()) if len(close) >= 126 else float(close.max())
    low_20 = float(close.tail(20).min())
    high_20 = float(close.tail(20).max())
    trend = "UP" if current > sma50 else "DOWN"
    score_to_high = round((current / high_6m) * 10, 1) if high_6m else 5.0
    band = abs(high_20 - low_20) / current if current else 1
    pattern = "Consolidating" if band < 0.05 else "Volatile"
    dist_support = (current - low_20) / current if current else 0
    dist_resist = (high_20 - current) / current if current else 0
    ret_20 = float(close.iloc[-1] / close.iloc[-21] - 1) if len(close) > 21 else 0.0

    opportunity = 0.0
    if trend == "UP":
        opportunity += 2.0
    else:
        opportunity += 0.5
    if pattern == "Consolidating" and dist_resist < 0.02:
        opportunity += 2.5
    if pattern == "Consolidating" and dist_support < 0.02:
        opportunity += 2.0
    if 0.02 < dist_support < 0.08 and trend == "UP":
        opportunity += 1.5
    opportunity += max(0.0, min(2.0, score_to_high / 5))
    opportunity += max(-1.0, min(1.5, ret_20 * 10))

    return {
        "current_price": current,
        "sma50": sma50,
        "trend": trend,
        "score": score_to_high,
        "pattern": pattern,
        "supportLevel": low_20,
        "resistanceLevel": high_20,
        "dist_to_support_pct": round(dist_support * 100, 2),
        "dist_to_resistance_pct": round(dist_resist * 100, 2),
        "return_20d_pct": round(ret_20 * 100, 2),
        "recent_closes": [round(float(x), 6) for x in close.tail(8).tolist()],
        "opportunity_score": round(opportunity, 3),
    }


def _download_batch(tickers: list[str]) -> pd.DataFrame | None:
    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="6mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
        return data
    except Exception:  # noqa: BLE001
        logger.exception("Batch download failed for %s tickers", len(tickers))
        return None


def _score_universe(universe: list[str]) -> tuple[list[dict[str, Any]], int]:
    scored: list[dict[str, Any]] = []
    scanned = 0
    for i in range(0, len(universe), SCREEN_BATCH_SIZE):
        batch = [normalize_symbol(t) for t in universe[i : i + SCREEN_BATCH_SIZE]]
        data = _download_batch(batch)
        if data is None or data.empty:
            continue
        scanned += len(batch)

        if len(batch) == 1:
            ticker = batch[0]
            try:
                close = data["Close"]
                feats = _score_row(close)
                if feats:
                    scored.append(
                        {
                            "ticker": ticker,
                            "asset_class": asset_class_for(ticker),
                            **feats,
                        }
                    )
            except Exception:  # noqa: BLE001
                continue
            continue

        for ticker in batch:
            try:
                close = data[ticker]["Close"]
                feats = _score_row(close)
                if feats:
                    scored.append(
                        {
                            "ticker": ticker,
                            "asset_class": asset_class_for(ticker),
                            **feats,
                        }
                    )
            except Exception:  # noqa: BLE001
                continue
    return scored, scanned


def _enrich_news(candidates: list[dict[str, Any]]) -> None:
    """Attach light news sentiment to top candidates only."""
    from analyzer import _analyzer, _news_title

    for item in candidates:
        ticker = item["ticker"]
        if item.get("asset_class") in {"forex", "crypto"}:
            # Yahoo news is thin for FX pairs; skip to save time
            item.setdefault("sentiment", "NEUTRAL")
            item.setdefault("news_headlines", [])
            continue
        try:
            raw = yf.Ticker(ticker).news or []
            scores = []
            headlines = []
            for n in raw[:4]:
                title = _news_title(n)
                if not title:
                    continue
                compound = _analyzer.polarity_scores(title)["compound"]
                scores.append(compound)
                headlines.append(
                    {
                        "title": title[:120],
                        "sentiment": (
                            "BULLISH"
                            if compound > 0.05
                            else "BEARISH"
                            if compound < -0.05
                            else "NEUTRAL"
                        ),
                    }
                )
            avg = sum(scores) / len(scores) if scores else 0.0
            sentiment = (
                "BULLISH" if avg > 0.05 else "BEARISH" if avg < -0.05 else "NEUTRAL"
            )
            item["sentiment"] = sentiment
            item["news_headlines"] = headlines
            if sentiment == "BULLISH":
                item["opportunity_score"] = round(item["opportunity_score"] + 0.8, 3)
            elif sentiment == "BEARISH":
                item["opportunity_score"] = round(item["opportunity_score"] - 0.5, 3)
        except Exception:  # noqa: BLE001
            item["sentiment"] = "NEUTRAL"
            item["news_headlines"] = []


def _load_cache() -> dict[str, Any] | None:
    if not SCREEN_CACHE_PATH.exists():
        return None
    try:
        return json.loads(SCREEN_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _save_cache(payload: dict[str, Any]) -> None:
    SCREEN_CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")


def screen_universe(
    *,
    top_n: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    top_n = top_n or SCREEN_TOP_N
    cached = _load_cache()
    if cached and not force:
        age_min = (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
        ).total_seconds() / 60
        if age_min < SCREEN_CACHE_MINUTES and cached.get("candidates"):
            return cached

    if AGENT_WATCHLIST:
        equity_universe = [normalize_symbol(t) for t in AGENT_WATCHLIST]
    else:
        equity_universe = get_sp500_tickers()

    equity_scored, equity_scanned = _score_universe(equity_universe)
    fx_scored, fx_scanned = _score_universe(FOREX_UNIVERSE)
    crypto_scored, crypto_scanned = _score_universe(CRYPTO_UNIVERSE)

    equity_scored.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
    fx_scored.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
    crypto_scored.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

    from ledger import load_portfolio

    held = [
        normalize_symbol(str(k))
        for k in (load_portfolio().get("positions") or {}).keys()
    ]

    shortlist = equity_scored[:top_n]
    shortlist.extend(fx_scored[:FX_CRYPTO_TOP_N])
    shortlist.extend(crypto_scored[:FX_CRYPTO_TOP_N])

    by_ticker = {
        c["ticker"]: c for c in (*equity_scored, *fx_scored, *crypto_scored)
    }
    for h in held:
        if h in by_ticker and all(c["ticker"] != h for c in shortlist):
            shortlist.append(by_ticker[h])

    _enrich_news(shortlist)
    shortlist.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

    sector_hint: dict[str, int] = {
        "UP_trend": 0,
        "DOWN_trend": 0,
        "Consolidating": 0,
        "Volatile": 0,
        "forex_candidates": len(fx_scored[:FX_CRYPTO_TOP_N]),
        "crypto_candidates": len(crypto_scored[:FX_CRYPTO_TOP_N]),
    }
    for c in equity_scored[:100]:
        sector_hint["UP_trend" if c["trend"] == "UP" else "DOWN_trend"] += 1
        sector_hint[c["pattern"]] = sector_hint.get(c["pattern"], 0) + 1

    universe_size = len(equity_universe) + len(FOREX_UNIVERSE) + len(CRYPTO_UNIVERSE)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "universe_size": universe_size,
        "scanned": equity_scanned + fx_scanned + crypto_scanned,
        "candidates": shortlist,
        "market_breadth": sector_hint,
    }
    _save_cache(payload)
    return payload
