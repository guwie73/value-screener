from __future__ import annotations

import pandas as pd

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

def get_sp500_tickers() -> list[str]:
    tables = pd.read_html(WIKI_SP500)
    df = tables[0]
    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    tickers = [str(x).strip().upper().replace(".", "-") for x in df[col].tolist()]
    # Deduplicate while preserving order
    seen = set()
    out = []
    for t in tickers:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out
