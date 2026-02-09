from __future__ import annotations

import os
import time
import streamlit as st

from finnhub import FinnhubClient
from financials_as_reported import parse_periods, build_fundamentals_from_reported
from buffett import buffett_screen
from graham import graham_screen
from sp500 import get_sp500_tickers
from stoxx import get_stoxx_europe_600
from cdax import get_de_exchange_equities
from world import get_msci_world_universe_via_etf

st.set_page_config(page_title="Value Screener", layout="wide")

QUOTE_TTL = 20
PROFILE_TTL = 24 * 60 * 60
REPORTED_TTL = 6 * 60 * 60
UNIVERSE_TTL = 24 * 60 * 60

def api_key() -> str:
    return (st.secrets.get("FINNHUB_API_KEY", None) or os.getenv("FINNHUB_API_KEY") or "").strip()

def score_combo(buffett_score: int, graham_score: int) -> int:
    # GANÉ-ish: quality > cheap (adjust later if desired)
    return int(round(0.65 * buffett_score + 0.35 * graham_score))

def verdict(score: int) -> str:
    if score >= 80: return "✅ Stark"
    if score >= 60: return "⚠️ Okay"
    return "❌ Schwach"

def normalize_shares(shares_raw: float | None) -> float | None:
    if shares_raw is None:
        return None
    s = float(shares_raw)
    # Heuristic: if very small, treat as "millions"
    if s < 100_000:
        return s * 1_000_000.0
    return s

@st.cache_data(ttl=QUOTE_TTL)
def get_quote(symbol: str) -> dict:
    return FinnhubClient(api_key=api_key()).quote(symbol)

@st.cache_data(ttl=PROFILE_TTL)
def get_profile(symbol: str) -> dict:
    return FinnhubClient(api_key=api_key()).profile2(symbol)

@st.cache_data(ttl=REPORTED_TTL)
def get_reported(symbol: str) -> dict:
    return FinnhubClient(api_key=api_key()).financials_reported(symbol)

@st.cache_data(ttl=UNIVERSE_TTL)
def load_universe(choice: str, world_etf: str = "URTH") -> list[str]:
    k = api_key()
    if choice == "S&P 500":
        return get_sp500_tickers()
    if choice == "STOXX Europe 600":
        return get_stoxx_europe_600()
    if choice == "CDAX (DE Exchange Approx)":
        if not k:
            return []
        return get_de_exchange_equities(k, exchange="DE")
    if choice == "World (MSCI World via ETF holdings)":
        if not k:
            return []
        return get_msci_world_universe_via_etf(k, etf_symbol=world_etf)
    return []

st.title("Value Screener (Graham / Buffett / GANÉ)")
st.caption("iPad-freundlich: Universe auswählen → laden → screen → Ranking + Gründe. Live Quotes + filings-nahe Fundamentals.")

with st.expander("Status / Freshness", expanded=False):
    st.write({
        "Quotes cache (sec)": QUOTE_TTL,
        "Fundamentals cache (hours)": REPORTED_TTL / 3600,
        "Universe refresh (hours)": UNIVERSE_TTL / 3600,
    })

choice = st.selectbox(
    "Universe",
    ["S&P 500", "STOXX Europe 600", "CDAX (DE Exchange Approx)", "World (MSCI World via ETF holdings)", "Manuelle Ticker"],
    index=0
)

world_etf = "URTH"
manual = ""
if choice == "World (MSCI World via ETF holdings)":
    world_etf = st.text_input("MSCI World ETF Symbol", value="URTH").strip().upper()
if choice == "Manuelle Ticker":
    manual = st.text_input("Tickers (kommagetrennt)", value="AAPL,MSFT,JNJ")

c1, c2, c3 = st.columns([1,1,1])
with c1:
    top_n = st.slider("Top N (für Speed)", 20, 300, 100, 10)
with c2:
    page_size = st.select_slider("Page size", options=[25, 50, 100, 200], value=100)
with c3:
    page = st.number_input("Page", min_value=1, value=1, step=1)

search = st.text_input("Optional: Filter (Ticker enthält…)", value="").strip().upper()

# Buffett thresholds
st.subheader("Filter")
col1, col2 = st.columns(2)
with col1:
    min_roic = st.slider("Min ROIC (Buffett)", 0.0, 0.30, 0.12, 0.01)
    min_margin = st.slider("Min Marge (Buffett)", 0.0, 0.50, 0.10, 0.01)
with col2:
    max_debt_fcf = st.slider("Max Debt/FCF (Jahre)", 0.0, 20.0, 5.0, 0.5)
    min_icov = st.slider("Min Interest Coverage", 0.0, 30.0, 5.0, 0.5)

if st.button("Universe laden"):
    if choice == "Manuelle Ticker":
        uni = [t.strip().upper() for t in manual.split(",") if t.strip()]
    else:
        if choice in ("CDAX (DE Exchange Approx)", "World (MSCI World via ETF holdings)") and not api_key():
            st.error("FINNHUB_API_KEY fehlt. (In Streamlit Secrets oder ENV setzen.)")
            st.stop()
        try:
            uni = load_universe(choice, world_etf=world_etf)
        except Exception as e:
            st.error(f"Universe konnte nicht geladen werden: {e}")
            uni = []
    if search:
        uni = [t for t in uni if search in t.upper()]
    st.session_state["universe"] = uni

uni = st.session_state.get("universe", [])
st.caption(f"Universe Größe: {len(uni)}")

# Select page slice + apply Top N cap
start = (page - 1) * int(page_size)
end = start + int(page_size)
tickers = uni[start:end][:top_n]

st.write(f"Screening-Liste: {len(tickers)} Ticker (Seite {page}, Größe {page_size}, TopN {top_n})")

def compute_pe_pb(price: float | None, shares_abs: float | None, ttm_netinc: float | None, equity: float | None) -> tuple[float | None, float | None]:
    pe = None
    pb = None
    if price is not None and shares_abs and ttm_netinc not in (None, 0):
        eps = float(ttm_netinc) / float(shares_abs)
        if eps != 0:
            pe = float(price) / eps
    if price is not None and shares_abs and equity not in (None, 0):
        book_per_share = float(equity) / float(shares_abs)
        if book_per_share != 0:
            pb = float(price) / book_per_share
    return pe, pb

if st.button("Screen"):
    if not tickers:
        st.warning("Keine Ticker ausgewählt. Erst Universe laden oder manuelle Ticker eingeben.")
        st.stop()
    if not api_key():
        st.error("FINNHUB_API_KEY fehlt. (In Streamlit Secrets oder ENV setzen.)")
        st.stop()

    rows = []
    progress = st.progress(0, text="Screening läuft…")

    for i, t in enumerate(tickers, start=1):
        try:
            q = get_quote(t)
            price = q.get("c", None)
            quote_ts = q.get("t", None)

            prof = get_profile(t)
            shares_abs = normalize_shares(prof.get("shareOutstanding", None))

            rep = get_reported(t)
            periods = parse_periods(rep)
            f = build_fundamentals_from_reported(periods)

            pe, pb = compute_pe_pb(price, shares_abs, f.get("ttm_netinc", None), f.get("bs_equity_avg2", None))
            f["pe"] = pe
            f["pb"] = pb

            b = buffett_screen(
                f,
                min_roic=min_roic,
                min_margin=min_margin,
                max_debt_to_fcf=max_debt_fcf,
                min_interest_coverage=min_icov,
            )
            g = graham_screen(f)
            combo = score_combo(b.score, g.score)

            rows.append({
                "ticker": t,
                "price": price,
                "quote_t": quote_ts,
                "score": combo,
                "buffett_pass": b.passed,
                "graham_pass": g.passed,
                "b": b,
                "g": g,
                "f": f,
            })
        except Exception as e:
            rows.append({"ticker": t, "price": None, "score": 0, "error": str(e)})

        progress.progress(i / max(1, len(tickers)), text=f"Screening läuft… {i}/{len(tickers)}")

    progress.empty()
    rows.sort(key=lambda r: r.get("score", 0), reverse=True)

    st.subheader("Ranking")
    for r in rows:
        t = r["ticker"]
        if "error" in r:
            st.markdown(f"### {t} — ❌ Fehler")
            st.error(r["error"])
            continue

        st.markdown(f"### {t} — {verdict(r['score'])} (Score {r['score']})")
        price = r.get("price")
        if price is not None:
            st.write(f"Preis: {price}")
        else:
            st.write("Preis: n/a")

        with st.expander("Warum / Details"):
            st.write("**Buffett**")
            for s in r["b"].reasons:
                st.write("• " + s)
            st.write("**Graham**")
            for s in r["g"].reasons:
                st.write("• " + s)

            f = r["f"]
            st.write("**Kennzahlen (berechnet)**")
            st.json({
                "roic": f.get("roic"),
                "operating_margin": f.get("operating_margin"),
                "debt_to_fcf": f.get("debt_to_fcf"),
                "interest_coverage": f.get("interest_coverage"),
                "current_ratio": f.get("current_ratio"),
                "debt_to_equity": f.get("debt_to_equity"),
                "pe": f.get("pe"),
                "pb": f.get("pb"),
                "ttm_fcf": f.get("ttm_fcf"),
            })
