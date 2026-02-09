from finnhub import FinnhubClient

def get_sp500_tickers(api_key: str) -> list[str]:
    client = FinnhubClient(api_key=api_key)
    data = client.stock_symbols(exchange="US")

    # Finnhub liefert viele Symbole – wir filtern auf “Common Stock”-ähnlich
    out = []
    for row in data:
        sym = (row.get("symbol") or "").strip().upper()
        typ = (row.get("type") or "").strip().upper()
        if not sym:
            continue
        if "STOCK" in typ or "COMMON" in typ or typ in ("EQS", "EQUITY", "SHARE"):
            out.append(sym)

    # Deduplicate
    seen = set()
    res = []
    for t in out:
        if t not in seen:
            seen.add(t)
            res.append(t)
    return res
