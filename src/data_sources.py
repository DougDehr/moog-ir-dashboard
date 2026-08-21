"""
All external data access lives here: Yahoo Finance (via yfinance) for prices
and market fundamentals, and SEC EDGAR (data.sec.gov) for filed financial
data and the filings list. Every public function is cached with st.cache_data
so the app stays responsive and polite to upstream services.
"""

from __future__ import annotations

import random
import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from curl_cffi import requests as cffi_requests
from yfinance.exceptions import YFRateLimitError

from src.config import sec_user_agent, COMPANY_CIK

SEC_BASE = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"


# ---------------------------------------------------------------------------
# Yahoo Finance access: Yahoo aggressively rate-limits/blocks the shared IP
# ranges that hosts like Streamlit Community Cloud use, independent of how
# polite this app's own request volume is (a well-documented, ongoing
# yfinance/Yahoo issue, not something fixable from app code alone). Two
# mitigations: impersonate a real browser's TLS/HTTP fingerprint via
# curl_cffi (yfinance's own current recommendation), and retry transient
# rate-limit responses with backoff before giving up.
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _yf_session():
    return cffi_requests.Session(impersonate="chrome")


def _yf_retry(fn, *args, retries: int = 2, base_delay: float = 1.5, **kwargs):
    """Call fn(*args, **kwargs), retrying a couple of times (short backoff) on
    a Yahoo rate-limit response. Re-raises the last error if all attempts fail,
    so callers keep their existing try/except handling unchanged."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except YFRateLimitError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(base_delay * (attempt + 1))
    raise last_exc


def _yf_stagger():
    """A small jittered pause before a fresh (cache-miss) Yahoo Finance call.

    Pages like Competitor Analysis/Analysts/Ownership/Export call
    get_fundamentals() for ~8 tickers in a tight loop. Right after a deploy
    (in-memory cache is empty) that fires 8 requests back-to-back with zero
    spacing, which reads as a burst/scrape pattern to Yahoo's rate limiter.
    This only runs inside a cached function's body, so it's paid once per
    unique ticker per cache window, never on a cache hit.
    """
    time.sleep(random.uniform(0.2, 0.5))


def _sec_stagger():
    """Same idea as _yf_stagger(), for SEC EDGAR. The Financials page's
    12-month backlog section checks 2 concepts x 8 companies (16 requests)
    in a tight loop with a cold cache, on top of whatever else the page
    already fetches — SEC's fair-access policy explicitly reserves the
    right to temporarily block an IP for bursty/excessive requests. SEC is
    generally more generous than Yahoo, so a lighter pause is enough.
    """
    time.sleep(random.uniform(0.1, 0.25))


# ---------------------------------------------------------------------------
# Yahoo Finance — price history
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60 * 45, show_spinner=False)
def get_price_history(tickers: tuple[str, ...], period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    """Adjusted close price history for one or more tickers. Columns = tickers."""
    if not tickers:
        return pd.DataFrame()
    try:
        data = _yf_retry(
            yf.download,
            list(tickers),
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
            session=_yf_session(),
        )
    except Exception:  # pragma: no cover - network dependent
        return pd.DataFrame()

    if data is None or data.empty:
        return pd.DataFrame()

    if len(tickers) == 1:
        close = data["Close"].to_frame(tickers[0])
    else:
        close = pd.DataFrame({t: data[t]["Close"] for t in tickers if t in data.columns.get_level_values(0)})
    close = close.dropna(how="all")
    return close


@st.cache_data(ttl=60 * 20, show_spinner=False)
def get_quote(ticker: str) -> dict:
    """Lightweight current-price snapshot for a single ticker."""
    try:
        _yf_stagger()
        tk = yf.Ticker(ticker, session=_yf_session())
        fast = _yf_retry(lambda: tk.fast_info)
        if not fast:
            return {"ticker": ticker, "error": "empty response from Yahoo Finance"}
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


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_fundamentals(ticker: str) -> dict:
    """Best-effort fundamentals snapshot (valuation + margin metrics) for one ticker."""
    try:
        _yf_stagger()
        tk = yf.Ticker(ticker, session=_yf_session())
        info = _yf_retry(tk.get_info)
    except Exception as exc:  # pragma: no cover - network dependent
        return {"ticker": ticker, "error": str(exc)}

    # get_info() can come back empty/None on a degraded (but non-exception-
    # raising) response from Yahoo — e.g. a soft rate-limit that returns a
    # 200 with no data — rather than always raising. Treat that the same as
    # any other fetch failure instead of crashing on info.get() below.
    if not info:
        return {"ticker": ticker, "error": "empty response from Yahoo Finance"}

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
        "currentPrice": g("currentPrice"),
        "targetHighPrice": g("targetHighPrice"),
        "targetLowPrice": g("targetLowPrice"),
        "targetMeanPrice": g("targetMeanPrice"),
        "targetMedianPrice": g("targetMedianPrice"),
        "numberOfAnalystOpinions": g("numberOfAnalystOpinions"),
        "recommendationKey": g("recommendationKey"),
        "recommendationMean": g("recommendationMean"),
        "sharesShort": g("sharesShort"),
        "sharesShortPriorMonth": g("sharesShortPriorMonth"),
        "shortRatio": g("shortRatio"),
        "shortPercentOfFloat": g("shortPercentOfFloat"),
        "averageVolume": g("averageVolume"),
        "averageVolume10days": g("averageVolume10days"),
        "floatShares": g("floatShares"),
        "sharesOutstanding": g("sharesOutstanding"),
        "heldPercentInsiders": g("heldPercentInsiders"),
        "heldPercentInstitutions": g("heldPercentInstitutions"),
    }


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_recommendations_trend(ticker: str) -> pd.DataFrame:
    """Monthly buy/hold/sell analyst-count trend (current month + prior 3), from Yahoo Finance."""
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        df = _yf_retry(lambda: tk.recommendations)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    return df


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_upgrades_downgrades(ticker: str, limit: int = 25) -> pd.DataFrame:
    """Recent analyst rating/price-target actions (firm, grade change, price target) from Yahoo Finance."""
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        df = _yf_retry(lambda: tk.upgrades_downgrades)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.reset_index().sort_values("GradeDate", ascending=False).head(limit)
    return df


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_major_holders_breakdown(ticker: str) -> dict:
    """Insider/institution ownership % breakdown from Yahoo Finance."""
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        mh = _yf_retry(lambda: tk.major_holders)
    except Exception:
        return {}
    if mh is None or mh.empty or "Value" not in mh.columns:
        return {}
    return mh["Value"].to_dict()


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_institutional_holders(ticker: str, limit: int = 10) -> pd.DataFrame:
    """Top institutional holders (name, shares, % held, value, QoQ change) from Yahoo Finance."""
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        df = _yf_retry(lambda: tk.institutional_holders)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    return df.head(limit)


# Rough classifier for insider-transaction free text, since yfinance's own
# 'Transaction' column is blank for most filers. Order matters (checked top
# to bottom); falls back to "Other".
_INSIDER_TEXT_RULES = [
    ("sale", "Sale"),
    ("purchase", "Purchase"),
    ("gift", "Gift"),
    ("conversion", "Option Exercise / Conversion"),
    ("exercise", "Option Exercise / Conversion"),
    ("award", "Award"),
]


def _classify_insider_text(text: str) -> str:
    t = (text or "").lower()
    for needle, label in _INSIDER_TEXT_RULES:
        if needle in t:
            return label
    return "Other"


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_insider_transactions(ticker: str, limit: int = 25) -> pd.DataFrame:
    """Recent Form 4 insider transactions (name, role, action, shares, value) from Yahoo Finance."""
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        df = _yf_retry(lambda: tk.insider_transactions)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["Action"] = df.get("Text", "").apply(_classify_insider_text)
    if "Start Date" in df.columns:
        df = df.sort_values("Start Date", ascending=False)
    return df.head(limit)


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_earnings_history(ticker: str, limit: int = 12) -> pd.DataFrame:
    """Trailing quarterly EPS estimate vs. actual and surprise %, from Yahoo Finance."""
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        df = _yf_retry(lambda: tk.earnings_dates)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.reset_index().rename(columns={"index": "Earnings Date"})
    df = df.dropna(subset=["Reported EPS"]).sort_values(df.columns[0])
    return df.tail(limit)


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_eps_trend(ticker: str) -> pd.DataFrame:
    """Consensus current-quarter/current-year EPS estimate now vs. 7/30/60/90 days ago."""
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        df = _yf_retry(lambda: tk.eps_trend)
    except Exception:
        return pd.DataFrame()
    return df if df is not None else pd.DataFrame()


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_dividends(ticker: str, period: str = "5y") -> pd.Series:
    try:
        tk = yf.Ticker(ticker, session=_yf_session())
        div = _yf_retry(lambda: tk.dividends)
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


def _sec_get_raw(url: str) -> requests.Response | None:
    """Like _sec_get, but returns the response for ANY HTTP-level reply
    (including 404), not just 200. None means the request never got an HTTP
    response at all (network error, timeout, DNS failure). Used where the
    caller needs to distinguish 'this concept genuinely isn't tagged'
    (404 — common and expected, e.g. a company that doesn't disclose a given
    ASC 606 item) from 'the fetch itself failed' (an external SEC EDGAR
    issue) — _sec_get alone can't tell those apart, since both come back as
    None."""
    try:
        return requests.get(url, headers={"User-Agent": sec_user_agent()}, timeout=15)
    except Exception:
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
    # Standard ASC 606 disclosures. "Backlog" itself is a voluntary, company-
    # defined metric with no XBRL tag of its own (confirmed: Moog's own
    # companyfacts has no tag containing "backlog"). These two, combined, are
    # a close structured-data proxy: total contracted-but-unrecognized revenue,
    # and the % of it the company expects to recognize within 12 months —
    # multiplying them reproduces Moog's own disclosed "twelve-month backlog"
    # to within rounding. Not every company discloses the percentage split
    # (some only disclose the total, some don't disclose either at all).
    "remaining_performance_obligation": ["RevenueRemainingPerformanceObligation"],
    "remaining_performance_obligation_pct": ["RevenueRemainingPerformanceObligationPercentage"],
}


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_concept_disclosure_status(cik: str, tag: str, taxonomy: str = "us-gaap") -> str:
    """Tri-state check for a company's XBRL facts, distinguishing a genuine
    absence from a fetch failure: 'has_data' (200, parses fine),
    'not_tagged' (404 — the company simply doesn't file this concept, a
    normal and expected outcome for optional ASC 606 disclosures like
    backlog-related items), or 'fetch_failed' (anything else: network
    error, timeout, rate-limit, 5xx — an external SEC EDGAR issue, not a
    real answer about the company's disclosures)."""
    cik10 = str(cik).zfill(10)
    url = f"{SEC_BASE}/api/xbrl/companyconcept/CIK{cik10}/{taxonomy}/{tag}.json"
    resp = _sec_get_raw(url)
    if resp is None:
        return "fetch_failed"
    if resp.status_code == 404:
        return "not_tagged"
    if resp.status_code != 200:
        return "fetch_failed"
    try:
        resp.json()
    except Exception:
        return "fetch_failed"
    return "has_data"


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_xbrl_concept(cik: str, tag: str, taxonomy: str = "us-gaap") -> pd.DataFrame:
    _sec_stagger()
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
