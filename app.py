"""
Moog Inc. — Investor Relations Dashboard (Overview)

Independent, unofficial dashboard built entirely from public data sources
(Yahoo Finance, SEC EDGAR). Structured to mirror the sections Moog itself
uses on its investor relations site: Overview / Stock / Financials /
Competitors / Filings.
"""

import streamlit as st
import pandas as pd

from src import config
from src.data_sources import get_quote, get_financial_series, quarterly_from_concept
from src.charts import fmt_money, fmt_pct
from src.theme import inject_moog_theme

st.set_page_config(
    page_title="Moog Inc. — Investor Relations Dashboard",
    page_icon="✈️",
    layout="wide",
)
inject_moog_theme()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

col_title, col_badge = st.columns([5, 2])
with col_title:
    st.title("✈️ Moog Inc. — Investor Relations Dashboard")
    st.caption(
        f"Precision motion control • {config.COMPANY_HQ} • NYSE: MOG.A / MOG.B  ·  "
        "Unofficial dashboard, not affiliated with Moog Inc."
    )
with col_badge:
    st.link_button("Official Moog IR Site ↗", config.IR_LINKS["Investor Relations Home"], use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Live quote strip — both share classes
# ---------------------------------------------------------------------------

st.subheader("Market Snapshot")
quote_cols = st.columns(len(config.SHARE_CLASSES) + 2)

for i, (label, ticker) in enumerate(config.SHARE_CLASSES.items()):
    q = get_quote(ticker)
    with quote_cols[i]:
        if "error" in q or q.get("last_price") != q.get("last_price"):
            st.metric(label, "n/a")
        else:
            change = q["last_price"] - q["prev_close"] if q.get("prev_close") else None
            pct_change = (change / q["prev_close"]) if change is not None and q.get("prev_close") else None
            st.metric(
                label,
                f"${q['last_price']:,.2f}",
                delta=f"{change:+.2f} ({pct_change*100:+.2f}%)" if change is not None else None,
            )

with quote_cols[-2]:
    q_a = get_quote(config.PRIMARY_TICKER)
    st.metric("Market Cap (Class A basis)", fmt_money(q_a.get("market_cap")))
with quote_cols[-1]:
    st.metric("52-Wk Range (Class A)",
               f"${q_a.get('year_low', float('nan')):,.0f}–${q_a.get('year_high', float('nan')):,.0f}"
               if q_a.get("year_low") else "n/a")

st.caption("Prices delayed per data vendor terms; refreshed on a ~15–30 minute cache cycle. Source: Yahoo Finance.")

# ---------------------------------------------------------------------------
# Latest reported quarter — KPI callout (mirrors Moog's "Latest Financial
# Results" box on ir.moog.com)
# ---------------------------------------------------------------------------

st.subheader("Latest Reported Quarter (SEC EDGAR XBRL)")

rev_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "revenue"))
ni_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "net_income"))
eps_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "diluted_eps"))
opinc_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "operating_income"))

k1, k2, k3, k4 = st.columns(4)


def _latest_two(df):
    if df.empty or len(df) < 1:
        return None, None
    latest = df.iloc[-1]
    prior_year = df[df["end"] <= latest["end"] - pd.DateOffset(months=11)]
    py = prior_year.iloc[-1] if not prior_year.empty else None
    return latest, py


rev_latest, rev_py = _latest_two(rev_df)
ni_latest, ni_py = _latest_two(ni_df)
eps_latest, eps_py = _latest_two(eps_df)
op_latest, op_py = _latest_two(opinc_df)

with k1:
    if rev_latest is not None:
        yoy = (rev_latest["val"] / rev_py["val"] - 1) if rev_py is not None and rev_py["val"] else None
        st.metric(f"Net Sales — Qtr ended {rev_latest['end'].date()}", fmt_money(rev_latest["val"]),
                  delta=fmt_pct(yoy) + " YoY" if yoy is not None else None)
    else:
        st.metric("Net Sales", "n/a")
with k2:
    if op_latest is not None and rev_latest is not None and rev_latest["val"]:
        margin = op_latest["val"] / rev_latest["val"]
        st.metric("Operating Margin", fmt_pct(margin))
    else:
        st.metric("Operating Margin", "n/a")
with k3:
    if ni_latest is not None:
        yoy = (ni_latest["val"] / ni_py["val"] - 1) if ni_py is not None and ni_py["val"] else None
        st.metric("Net Income", fmt_money(ni_latest["val"]),
                  delta=fmt_pct(yoy) + " YoY" if yoy is not None else None)
    else:
        st.metric("Net Income", "n/a")
with k4:
    if eps_latest is not None:
        st.metric("Diluted EPS", f"${eps_latest['val']:.2f}")
    else:
        st.metric("Diluted EPS", "n/a")

st.caption(
    "Figures are quarterly (not year-to-date) values derived from Moog's XBRL-tagged filings on SEC EDGAR. "
    "Moog also reports a twelve-month backlog figure each quarter in its earnings release — see "
    "[Financials & Filings](/Financials) and the official "
    f"[Financial Materials page]({config.IR_LINKS['Financials']})."
)

st.divider()

# ---------------------------------------------------------------------------
# Why Invest pillars
# ---------------------------------------------------------------------------

st.subheader("Why Invest in Moog?")
st.caption("Summarized from Moog's own investor relations positioning.")
pcols = st.columns(len(config.WHY_INVEST_PILLARS))
for c, (title, body) in zip(pcols, config.WHY_INVEST_PILLARS):
    with c:
        st.markdown(f"**{title}**")
        st.caption(body)

st.divider()

# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------

st.subheader("Reportable Segments")
seg_cols = st.columns(4)
for c, (name, desc) in zip(seg_cols, config.SEGMENTS):
    with c:
        st.markdown(f"**{name}**")
        st.caption(desc)

st.divider()

# ---------------------------------------------------------------------------
# Quick nav to official IR sections + in-app pages
# ---------------------------------------------------------------------------

left, right = st.columns(2)
with left:
    st.subheader("In This Dashboard")
    st.page_link("pages/1_Stock_Performance.py", label="📈 Stock Performance vs. Competitors", icon="📈")
    st.page_link("pages/2_Competitor_Analysis.py", label="⚖️ Competitor Analysis", icon="⚖️")
    st.page_link("pages/3_Financials.py", label="💰 Financials Trend", icon="💰")
    st.page_link("pages/4_Filings_and_Events.py", label="📰 Filings & Events", icon="📰")
    st.page_link("pages/5_About.py", label="ℹ️ About & Data Sources", icon="ℹ️")

with right:
    st.subheader("Official Moog IR Site")
    for label, url in config.IR_LINKS.items():
        st.markdown(f"- [{label}]({url})")

st.divider()
st.caption(config.DISCLAIMER)
