"""Shared market analysis pipeline for API and AI agent."""

from __future__ import annotations

from typing import Any

import numpy as np
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def _news_title(item: dict) -> str:
    if not isinstance(item, dict):
        return ""
    title = item.get("title") or item.get("headline")
    if title:
        return str(title)
    content = item.get("content")
    if isinstance(content, dict):
        return str(content.get("title") or content.get("summary") or "")
    return ""


def _news_link(item: dict) -> str:
    if not isinstance(item, dict):
        return "#"
    link = item.get("link") or item.get("url")
    if link:
        return str(link)
    content = item.get("content")
    if isinstance(content, dict):
        click = content.get("clickThroughUrl") or content.get("canonicalUrl") or {}
        if isinstance(click, dict):
            return str(click.get("url") or "#")
        if isinstance(click, str):
            return click
    return "#"


def analyze_ticker(ticker: str, *, include_series: bool = True) -> dict[str, Any]:
    ticker = ticker.upper().strip()
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo")
    if hist.empty:
        raise ValueError(f"No data found for {ticker}")

    hist = hist.reset_index()
    hist["date"] = hist["Date"].dt.strftime("%Y-%m-%d")

    hist["SMA_50"] = hist["Close"].rolling(window=50).mean()
    current_price = float(hist["Close"].iloc[-1])
    sma_50 = (
        float(hist["SMA_50"].iloc[-1])
        if not np.isnan(hist["SMA_50"].iloc[-1])
        else current_price
    )

    trend = "UP" if current_price > sma_50 else "DOWN"
    high_6m = float(hist["High"].max())
    score = round((current_price / high_6m) * 10, 1)

    support = float(hist["Low"].rolling(window=20).min().iloc[-1])
    resistance = float(hist["High"].rolling(window=20).max().iloc[-1])
    pattern = (
        "Consolidating"
        if abs(resistance - support) / current_price < 0.05
        else "Volatile"
    )

    raw_news = stock.news or []
    sentiment_score = 0.0
    news_data: list[dict[str, Any]] = []

    for n in raw_news[:6]:
        title = _news_title(n)
        if not title:
            continue
        compound = _analyzer.polarity_scores(title)["compound"]
        sentiment_score += compound
        news_data.append(
            {
                "title": title,
                "link": _news_link(n),
                "sentiment": (
                    "BULLISH"
                    if compound > 0.05
                    else "BEARISH"
                    if compound < -0.05
                    else "NEUTRAL"
                ),
                "score": compound,
            }
        )

    avg_sentiment = sentiment_score / len(news_data) if news_data else 0.0
    sentiment_label = (
        "BULLISH"
        if avg_sentiment > 0.05
        else "BEARISH"
        if avg_sentiment < -0.05
        else "NEUTRAL"
    )

    result: dict[str, Any] = {
        "ticker": ticker,
        "current_price": current_price,
        "sma50": sma_50,
        "trend": trend,
        "score": score,
        "pattern": pattern,
        "sentiment": sentiment_label,
        "supportLevel": support,
        "resistanceLevel": resistance,
        "news": news_data,
        "breakoutPoints": [],
    }

    if include_series:
        result["history"] = [
            {
                "date": row["date"],
                "price": float(row["Close"]),
                "sma50": float(row["SMA_50"]) if not np.isnan(row["SMA_50"]) else None,
            }
            for _, row in hist.iterrows()
        ]
        result["volume"] = [
            {"date": row["date"], "volume": float(row["Volume"])}
            for _, row in hist.iterrows()
        ]
    else:
        # Compact snapshot for LLM prompts
        result["recent_closes"] = [
            round(float(x), 2) for x in hist["Close"].tail(10).tolist()
        ]

    return result
