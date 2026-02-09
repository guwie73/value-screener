from __future__ import annotations

from src.providers.finnhub import FinnhubClient

def get_msci_world_universe_via_etf(api_key: str, etf_symbol: str = "URTH") -> list[str]:
    client = FinnhubClient(api_key=api_key)
    payload = client.etf_holdings(symbol=etf_symbol)
    holdings = (payload or {}).get("holdings", []) or []
    tickers = []
    for h in holdings:
        sym = (h.get("symbol") or "").strip().upper()
        if sym:
            tickers.append(sym)

    # Deduplicate
    seen = set()
    out = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
