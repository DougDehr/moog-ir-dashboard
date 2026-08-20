"""
All external data access lives here: Yahoo Finance (via yfinance) for prices
and market fundamentals, and SEC EDGAR (data.sec.gov) for filed financial
data and the filings list. Every public function is cached with st.cache_data
so the app stays responsive and polite to upstream services.
"""

from __future__ import annotations

import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from src.config import sec_user_agent, COMPANY_CIK

SEC_BASE = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"


# ---------------------------------------------------------------------------
# Yahoo Finance — price history
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60 * 30, show_spinner=False)
def get_price_history(tickers: tuple[str, ...], period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    """Adjusted close price history for one or more tickers. Columns = tickers."""
    if not tickers:
        return pd.DataFrame()
    data = yf.download(
        list(tickers),
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    if data.empty:
        return pd.DataFrame()

    if len(tickers) == 1:
        close = data["Close"].to_frame(tickers[0])
    else:
        close = pd.DataFrame({t: data[t]["Close"] for t in tickers if t in data.columns.get_level_values(0)})
    close = close.dropna(how="all")
    return close


@st.cache_data(ttl=60 * 15, show_spinner=False)
def get_quote(ticker: str) -> dict:
    """Lightweight current-price snapshot for a single ticker."""
    try:
        tk = yf.Ticker(ticker)
        fast = tk.fast_info
        return {
            "ticker": ticker,
            "last_price": float(fast.get("lastPrice", np.nan)),
            "prev_close": float(fast.get("previousClose", np.nan)),
            "market_cap": fast.get("marketCap", None),
            "currency": fast.get("currency", "USD"),
            "day_high": fast.get("dayHigh", None),
            "day_low": fast.get("dayLow", None),
            "year_high": fast.get("yearHigh", None),
            "year_low": fast.get("yearLow", None),
        }
    except Exception as exc:  # pragma: no cover - network dependent
        return {"ticker": ticker, "error": str(exc)}


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_fundamentals(ticker: str) -> dict:
    """Best-effort fundamentals snapshot (valuation + margin metrics) for one ticker."""
    try:
        tk = yf.Ticker(ticker)
        info = tk.get_info()
    except Exception as exc:  # pragma: no cover - network dependent
        return {"ticker": ticker, "error": str(exc)}

    def g(key, default=None):
        return info.get(key, default)

    return {
        "ticker": ticker,
        "shortName": g("shortName", ticker),
        "sector": g("sector"),
        "industry": g("industry"),
        "marketCap": g("marketCap"),
        "trailingPE": g("trailingPE"),
        "forwardPE": g("forwardPE"),
        "priceToSalesTrailing12Months": g("priceToSalesTrailing12Months"),
        "enterpriseToEbitda": g("enterpriseToEbitda"),
        "enterpriseToRevenue": g("enterpriseToRevenue"),
        "profitMargins": g("profitMargins"),
        "grossMargins": g("grossMargins"),
        "operatingMargins": g("operatingMargins"),
        "ebitdaMargins": g("ebitdaMargins"),
        "revenueGrowth": g("revenueGrowth"),
        "earningsGrowth": g("earningsGrowth"),
        "returnOnEquity": g("returnOnEquity"),
        "debtToEquity": g("debtToEquity"),
        "dividendYield": g("dividendYield"),
        "beta": g("beta"),
        "totalRevenue": g("totalRevenue"),
        "trailingEps": g("trailingEps"),
        "fiftyTwoWeekHigh": g("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": g("fiftyTwoWeekLow"),
    }


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_dividends(ticker: str, period: str = "5y") -> pd.Series:
    try:
        tk = yf.Ticker(ticker)
        div = tk.dividends
        if div is None or div.empty:
            return pd.Series(dtype=float)
        div.index = div.index.tz_localize(None)
        cutoff = pd.Timestamp.now() - pd.tseries.offsets.DateOffset(years=int(period[:-1]) if period.endswith("y") else 5)
        return div[div.index >= cutoff]
    except Exception:
        return pd.Series(dtype=float)


# ---------------------------------------------------------------------------
# SEC EDGAR — filings + structured financial facts
# ---------------------------------------------------------------------------

def _sec_get(url: str) -> requests.Response | None:
    try:
        resp = requests.get(url, headers={"User-Agent": sec_user_agent()}, timeout=15)
        if resp.status_code == 200:
            return resp
    except Exception:
        pass
    return None


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_company_tickers_map() -> dict:
    """ticker(upper) -> 10-digit zero-padded CIK, from SEC's canonical public list."""
    resp = _sec_get(f"{SEC_WWW}/files/company_tickers.json")
    if resp is None:
        return {}
    try:
        raw = resp.json()
    except Exception:
        return {}
    out = {}
    for entry in raw.values():
        out[str(entry["ticker"]).upper()] = str(entry["cik_str"]).zfill(10)
    return out


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_recent_filings(cik: str, forms: tuple[str, ...] = ("10-K", "10-Q", "8-K"), limit: int = 12) -> pd.DataFrame:
    """Recent filings for a CIK from SEC's submissions API."""
    cik10 = str(cik).zfill(10)
    resp = _sec_get(f"{SEC_BASE}/submissions/CIK{cik10}.json")
    if resp is None:
        return pd.DataFrame()
    try:
        j = resp.json()
    except Exception:
        return pd.DataFrame()

    recent = j.get("filings", {}).get("recent", {})
    if not recent:
        return pd.DataFrame()

    df = pd.DataFrame(recent)
    if df.empty:
        return df
    df = df[df["form"].isin(forms)].copy()
    df = df.sort_values("filingDate", ascending=False).head(limit)

    def _index_url(accession, cik_):
        acc_nodash = accession.replace("-", "")
        return f"{SEC_WWW}/Archives/edgar/data/{int(cik_)}/{acc_nodash}/{accession}-index.htm"

    df["url"] = df["accessionNumber"].apply(lambda a: _index_url(a, cik10))
    return df[["filingDate", "form", "primaryDocDescription", "reportDate", "url"]].reset_index(drop=True)


# XBRL concept tags to try, in priority order, per financial line item.
# Different filers/years use different GAAP tags for the "same" concept.
_CONCEPT_CANDIDATES = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "net_income": ["NetIncomeLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "diluted_eps": ["EarningsPerShareDiluted"],
    "basic_eps": ["EarningsPerShareBasic"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
}


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_xbrl_concept(cik: str, tag: str, taxonomy: str = "us-gaap") -> pd.DataFrame:
    cik10 = str(cik).zfill(10)
    resp = _sec_get(f"{SEC_BASE}/api/xbrl/companyconcept/CIK{cik10}/{taxonomy}/{tag}.json")
    if resp is None:
        return pd.DataFrame()
    try:
        j = resp.json()
    except Exception:
        return pd.DataFrame()

    rows = []
    for unit, entries in j.get("units", {}).items():
        for e in entries:
            rows.append({
                "unit": unit,
                "start": e.get("start"),
                "end": e.get("end"),
                "val": e.get("val"),
                "fy": e.get("fy"),
                "fp": e.get("fp"),
                "form": e.get("form"),
                "frame": e.get("frame"),
                "filed": e.get("filed"),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["end"] = pd.to_datetime(df["end"])
    df["start"] = pd.to_datetime(df["start"])
    df["filed"] = pd.to_datetime(df["filed"])
    return df.sort_values("end")


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_financial_series(cik: str, concept_key: str) -> pd.DataFrame:
    """Try each candidate GAAP tag for a concept until one returns data."""
    for tag in _CONCEPT_CANDIDATES.get(concept_key, []):
        df = get_xbrl_concept(cik, tag)
        if not df.empty:
            df["concept"] = concept_key
            df["tag"] = tag
            return df
    return pd.DataFrame()


def quarterly_from_concept(df: pd.DataFrame, forms: tuple[str, ...] = ("10-Q", "10-K")) -> pd.DataFrame:
    """Collapse a raw XBRL concept frame (duration facts) to one value per fiscal quarter-end.

    Keeps the most-recently-filed value for each unique period, restricted to
    roughly-quarterly duration facts (~80-100 days) so we don't mix in
    9-month or full-year cumulative figures.
    """
    if df.empty:
        return df
    d = df[df["form"].isin(forms)].copy()
    if d.empty:
        return d
    d["days"] = (d["end"] - d["start"]).dt.days
    d = d[(d["days"] >= 70) & (d["days"] <= 100)]
    if d.empty:
        return d
    d = d.sort_values(["end", "filed"]).drop_duplicates(subset=["end"], keep="last")
    return d.sort_values("end")


def as_value_series(df: pd.DataFrame, index_col: str = "end") -> pd.Series:
    """Safely convert a (possibly empty) concept frame to a Series indexed by period-end.

    Guards against the common failure mode where an upstream XBRL concept
    returns no data at all (e.g. a peer tags a line item differently), which
    would otherwise raise a KeyError on .set_index() against a columnless
    empty DataFrame.
    """
    if df.empty or index_col not in df.columns:
        return pd.Series(dtype=float)
    return df.set_index(index_col)["val"]


def instant_series(df: pd.DataFrame, forms: tuple[str, ...] = ("10-Q", "10-K")) -> pd.DataFrame:
    """For balance-sheet ('instant') concepts: one value per period end, latest filing wins."""
    if df.empty:
        return df
    d = df[df["form"].isin(forms)].copy()
    if d.empty:
        return d
    d = d.sort_values(["end", "filed"]).drop_duplicates(subset=["end"], keep="last")
    return d.sort_values("end")
