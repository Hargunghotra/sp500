"""Asset helpers for equity / forex / crypto symbols."""

from __future__ import annotations


def normalize_symbol(symbol: str) -> str:
    s = symbol.strip()
    # Preserve yahoo FX/crypto forms
    if "=" in s or "-" in s:
        parts = s.split("-")
        if len(parts) == 2:
            return f"{parts[0].upper()}-{parts[1].upper()}"
        return s.upper() if s.endswith("=X") or "=X" in s.upper() else s.upper()
    return s.upper()


def asset_class_for(symbol: str) -> str:
    s = normalize_symbol(symbol)
    if s.endswith("=X") or "=X" in s:
        return "forex"
    if "-" in s and s.split("-")[-1] in {
        "USD",
        "USDT",
        "EUR",
        "BTC",
        "ETH",
    }:
        return "crypto"
    known_crypto = {
        "BTC-USD",
        "ETH-USD",
        "SOL-USD",
        "XRP-USD",
        "ADA-USD",
        "DOGE-USD",
        "AVAX-USD",
        "LINK-USD",
    }
    if s in known_crypto:
        return "crypto"
    return "equity"
