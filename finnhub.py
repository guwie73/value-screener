from __future__ import annotations

import os
import requests
from typing import Any, Dict

FINNHUB_BASE = "https://finnhub.io/api/v1"


class FinnhubClient:
    def __init__(self, api_key: str | None = None, timeout: int = 12):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY missing")
        self.timeout = timeout
        self.session = requests.Session()

    def quote(self, symbol: str) -> Dict[str, Any]:
        # Docs: /quote returns {c,h,l,o,pc,t}
        url = f"{FINNHUB_BASE}/quote"
        r = self.session.get(url, params={"symbol": symbol.upper(), "token": self.api_key}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def profile2(self, symbol: str) -> Dict[str, Any]:
        # Docs: /stock/profile2 includes shareOutstanding, marketCapitalization, etc.
        url = f"{FINNHUB_BASE}/stock/profile2"
        r = self.session.get(url, params={"symbol": symbol.upper(), "token": self.api_key}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def financials_reported(self, symbol: str) -> Dict[str, Any]:
        # Docs: /stock/financials-reported (filings-near)
        url = f"{FINNHUB_BASE}/stock/financials-reported"
        r = self.session.get(url, params={"symbol": symbol.upper(), "token": self.api_key}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def stock_symbols(self, exchange: str) -> list[dict[str, Any]]:
        # Docs: /stock/symbol
        url = f"{FINNHUB_BASE}/stock/symbol"
        r = self.session.get(url, params={"exchange": exchange, "token": self.api_key}, timeout=30)
        r.raise_for_status()
        data = r.json() or []
        if not isinstance(data, list):
            return []
        return data

    def etf_holdings(self, symbol: str) -> Dict[str, Any]:
        # Docs: /etf/holdings
        url = f"{FINNHUB_BASE}/etf/holdings"
        r = self.session.get(url, params={"symbol": symbol.upper(), "token": self.api_key}, timeout=30)
        r.raise_for_status()
        return r.json()
