# Value Screener Web App (iPad-ready) — Finnhub + Financials-as-Reported

A simple, public web app that screens stocks using Graham/Buffett/GANÉ-style logic with:
- **Live quotes** (Finnhub `/quote`, cached ~20s)
- **Filings-near fundamentals** (Finnhub `/stock/financials-reported`, cached ~6h)
- **Universes**: S&P 500, STOXX Europe 600, DE Exchange (CDAX approximation), World (MSCI World via ETF holdings, default `URTH`)
- **Laienfreundlich**: Dropdown → Load Universe → Screen → Ranking + ✅/⚠️/❌ + verständliche Gründe

## 1) Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FINNHUB_API_KEY="YOUR_KEY"   # mac/linux
# setx FINNHUB_API_KEY "YOUR_KEY"   # windows powershell

streamlit run src/app_streamlit.py
```

## 2) Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub.
2. Streamlit Cloud → **New app**
3. Main file path: `src/app_streamlit.py`
4. Add secret:
```toml
FINNHUB_API_KEY="YOUR_KEY"
```

## Notes
- Screening a full universe (500/600+) can hit API rate limits. The UI defaults to **Top N = 100** + pagination.
- STOXX export formats can vary. If STOXX load fails, the app shows a friendly message and you can still use other universes or manual tickers.
