from __future__ import annotations

import pandas as pd
import requests
from io import StringIO

def get_stoxx_europe_600() -> list[str]:
    """
    Best-effort: STOXX components export endpoint.
    Export formats can change; we try CSV first then HTML.
    """
    url = "https://stoxx.com/index/sxxp/?components=true&export=true&symbol=SXXP"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    text = r.text

    df = None
    try:
        df = pd.read_csv(StringIO(text))
    except Exception:
        dfs = pd.read_html(text)
        df = dfs[0]

    # Try common columns
    cols = {str(c).lower(): c for c in df.columns}
    for key in ("symbol", "ticker", "ric", "reuters"):
        if key in cols:
            col = cols[key]
            break
    else:
        col = df.columns[0]

    tickers = []
    for x in df[col].tolist():
        s = str(x).strip().upper()
        if s and s != "NAN":
            tickers.append(s)

    # Deduplicate
    seen = set()
    out = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
