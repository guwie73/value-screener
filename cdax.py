from __future__ import annotations

from typing import Any
from finnhub import FinnhubClient

def get_de_exchange_equities(api_key: str, exchange: str = "DE") -> list[str]:
    client = FinnhubClient(api_key=api_key)
    data = client.stock_symbols(exchange=exchange)
    tickers: list[str] = []
    for row in data:
        sym = (row.get("symbol") or "").strip().upper()
        typ = (row.get("type") or "").strip().upper()
        if not sym:
            continue
        # Keep equities-like
        if "STOCK" in typ or "COMMON" in typ or typ in ("EQS", "EQUITY", "SHARE"):
            tickers.append(sym)

    # Deduplicate
    seen = set()
    out = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
