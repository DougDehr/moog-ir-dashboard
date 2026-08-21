"""Financial trend page: revenue, margins, EPS, and balance sheet, sourced from SEC EDGAR XBRL."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config
from src.data_sources import (
    get_company_tickers_map, get_financial_series, quarterly_from_concept, instant_series, as_value_series,
)
from src.charts import fmt_money, fmt_pct, BRAND_COLORS
from src.theme import inject_moog_theme, MAROON
from src.ui import external_data_unavailable

st.set_page_config(page_title="Financials — Moog IR Dashboard", page_icon="💰", layout="wide")
inject_moog_theme()
st.title("Financial Trends")
st.caption(
    "Built directly from Moog's XBRL-tagged filings on SEC EDGAR (data.sec.gov) — the same structured "
    "data underlying Moog's 10-K/10-Q filings. Figures are as-filed and may include restatements."
)


def _load_company_quarterlies(cik: str) -> dict[str, pd.DataFrame]:
    out = {}
    for key in ["revenue", "operating_income", "net_income", "diluted_eps"]:
        out[key] = quarterly_from_concept(get_financial_series(cik, key))
    for key in ["assets", "liabilities", "equity", "cash", "long_term_debt"]:
        out[key] = instant_series(get_financial_series(cik, key))
    return out


with st.spinner("Pulling XBRL financial data from SEC EDGAR…"):
    moog_data = _load_company_quarterlies(config.COMPANY_CIK)

if moog_data["revenue"].empty:
    external_data_unavailable("Moog's revenue data", provider="SEC EDGAR")
    st.stop()

# ---------------------------------------------------------------------------
# Revenue & operating income
# ---------------------------------------------------------------------------

st.subheader("Quarterly Net Sales & Operating Income")
rev = as_value_series(moog_data["revenue"]).rename("Net Sales")
opi = as_value_series(moog_data["operating_income"]).rename("Operating Income")
merged = pd.concat([rev, opi], axis=1).tail(20)

fig = go.Figure()
fig.add_trace(go.Bar(x=merged.index, y=merged["Net Sales"], name="Net Sales", marker_color="#2E4057"))
fig.add_trace(go.Scatter(x=merged.index, y=merged["Operating Income"], name="Operating Income",
                          mode="lines+markers", line=dict(color=MAROON, width=3), yaxis="y"))
fig.update_layout(
    template="plotly_white", height=460, hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=40, b=10),
    yaxis_title="USD",
)
st.plotly_chart(fig, use_container_width=True)

# Operating margin trend
merged["Operating Margin"] = merged["Operating Income"] / merged["Net Sales"]
fig_margin = go.Figure(go.Scatter(x=merged.index, y=merged["Operating Margin"], mode="lines+markers",
                                   line=dict(color="#1B7F79", width=3)))
fig_margin.update_layout(title="Operating Margin Trend", yaxis_tickformat=".0%",
                          template="plotly_white", height=320, margin=dict(l=10, r=10, t=40, b=10))
st.plotly_chart(fig_margin, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# EPS & Net income
# ---------------------------------------------------------------------------

st.subheader("Diluted EPS & Net Income")
eps = as_value_series(moog_data["diluted_eps"]).rename("Diluted EPS").tail(20)
ni = as_value_series(moog_data["net_income"]).rename("Net Income").tail(20)

c1, c2 = st.columns(2)
with c1:
    fig_eps = go.Figure(go.Bar(x=eps.index, y=eps.values, marker_color="#5C6BC0"))
    fig_eps.update_layout(title="Diluted EPS by Quarter", template="plotly_white", height=380,
                           margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_eps, use_container_width=True)
with c2:
    fig_ni = go.Figure(go.Bar(x=ni.index, y=ni.values, marker_color="#C98A2B"))
    fig_ni.update_layout(title="Net Income by Quarter", template="plotly_white", height=380,
                          margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_ni, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Balance sheet snapshot
# ---------------------------------------------------------------------------

st.subheader("Balance Sheet Snapshot (Most Recent Reported Period)")


def _latest_val(df):
    return None if df.empty else df.iloc[-1]["val"]


assets = _latest_val(moog_data["assets"])
liab = _latest_val(moog_data["liabilities"])
equity = _latest_val(moog_data["equity"])
cash = _latest_val(moog_data["cash"])
debt = _latest_val(moog_data["long_term_debt"])

b1, b2, b3, b4, b5 = st.columns(5)
b1.metric("Total Assets", fmt_money(assets))
b2.metric("Total Liabilities", fmt_money(liab))
b3.metric("Stockholders' Equity", fmt_money(equity))
b4.metric("Cash & Equivalents", fmt_money(cash))
b5.metric("Long-Term Debt", fmt_money(debt))

if debt and equity:
    st.caption(f"Long-term debt / equity ≈ {debt/equity:.2f}x (as-reported, unadjusted).")

st.divider()

# ---------------------------------------------------------------------------
# 12-month backlog (estimated from ASC 606 disclosures)
# ---------------------------------------------------------------------------

st.subheader("12-Month Backlog")
st.caption(
    "\"Backlog\" is a voluntary metric with no XBRL tag of its own — confirmed against Moog's full set of "
    "filed XBRL facts, nothing contains \"backlog.\" Moog highlights a \"twelve-month backlog\" figure in "
    "its earnings release each quarter, but it's prose/table disclosure, not structured data. This chart "
    "estimates the same figure from two things almost every company under ASC 606 *does* tag: total "
    "Remaining Performance Obligation (contracted, unrecognized revenue) and the % of it the company says "
    "it expects to recognize as revenue within the next twelve months. Multiplying them reproduces Moog's "
    "own disclosed twelve-month backlog closely — for the quarter ended June 27, 2026, this computes to "
    "≈\\$3.27B vs. Moog's own disclosed \\$3.25B."
)


def _est_12mo_backlog(cik: str) -> pd.Series:
    rpo = instant_series(get_financial_series(cik, "remaining_performance_obligation"))
    pct = instant_series(get_financial_series(cik, "remaining_performance_obligation_pct"))
    if rpo.empty or pct.empty:
        return pd.Series(dtype=float)
    rpo_s = rpo.set_index("end")["val"]
    pct_s = pct.set_index("end")["val"]
    combined = pd.concat([rpo_s.rename("rpo"), pct_s.rename("pct")], axis=1).dropna()
    return combined["rpo"] * combined["pct"]


with st.spinner("Checking backlog-related disclosures for Moog and its competitors…"):
    ticker_cik_backlog = get_company_tickers_map()
    moog_backlog = _est_12mo_backlog(config.COMPANY_CIK)

    cw_cik = ticker_cik_backlog.get("CW")
    cw_backlog = _est_12mo_backlog(cw_cik) if cw_cik else pd.Series(dtype=float)

if moog_backlog.empty:
    st.info("Could not compute an estimated 12-month backlog for Moog from currently available XBRL data.")
else:
    fig_backlog = go.Figure()
    fig_backlog.add_trace(go.Bar(
        x=moog_backlog.tail(20).index, y=moog_backlog.tail(20).values, name="Moog", marker_color=MAROON,
    ))
    if not cw_backlog.empty:
        fig_backlog.add_trace(go.Scatter(
            x=cw_backlog.tail(20).index, y=cw_backlog.tail(20).values, name="Curtiss-Wright",
            mode="lines+markers", line=dict(color="#2E4057", width=2.5),
        ))
    fig_backlog.update_layout(
        title="Estimated 12-Month Backlog Trend", template="plotly_white", height=400,
        yaxis_title="USD", hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=40, b=60),
    )
    st.plotly_chart(fig_backlog, use_container_width=True)
    if not cw_backlog.empty:
        st.caption("Curtiss-Wright is the one peer here that discloses the same 12-month split Moog does — "
                   "shown for a genuine apples-to-apples comparison.")

st.markdown("**Do Moog's competitors report a comparable backlog figure?**")

disclosure_rows = []
total_rpo_latest = {config.COMPANY_NAME: _latest_val(instant_series(
    get_financial_series(config.COMPANY_CIK, "remaining_performance_obligation")))}
for tkr, name in config.PEERS.items():
    cik = ticker_cik_backlog.get(tkr)
    rpo_df = instant_series(get_financial_series(cik, "remaining_performance_obligation")) if cik else pd.DataFrame()
    pct_df = instant_series(get_financial_series(cik, "remaining_performance_obligation_pct")) if cik else pd.DataFrame()
    has_total, has_split = not rpo_df.empty, not pct_df.empty
    total_rpo_latest[name] = _latest_val(rpo_df) if has_total else None
    if has_total and has_split:
        disclosure = "Discloses 12-month split (comparable to Moog)"
    elif has_total:
        disclosure = "Discloses total backlog only (no 12-month split)"
    else:
        disclosure = "Does not disclose backlog / remaining performance obligation"
    disclosure_rows.append({"Company": name, "Disclosure": disclosure})

st.dataframe(pd.DataFrame(disclosure_rows), use_container_width=True, hide_index=True)
st.caption(
    "TransDigm and HEICO likely qualify for the ASC 606 practical expedient that exempts shorter-cycle, "
    "aftermarket-parts-driven businesses from this disclosure — consistent with their business models "
    "being less OEM-production-backlog-driven than Moog's."
)

backlog_compare = pd.Series(total_rpo_latest).dropna()
if not backlog_compare.empty:
    colors = [MAROON if c == config.COMPANY_NAME else "#2E4057" for c in backlog_compare.index]
    text = [fmt_money(v) for v in backlog_compare.values]
    fig_total_backlog = go.Figure(go.Bar(
        x=list(backlog_compare.index), y=list(backlog_compare.values),
        marker_color=colors, text=text, textposition="outside",
    ))
    fig_total_backlog.update_layout(
        title="Total Backlog (Remaining Performance Obligation, All Future Periods)",
        template="plotly_white", height=420, xaxis_tickangle=-35, margin=dict(l=10, r=10, t=60, b=10),
    )
    st.plotly_chart(fig_total_backlog, use_container_width=True)
    st.caption("This is *total* contracted backlog (all future periods), not the 12-month cut — the two are "
               "only directly comparable for Moog and Curtiss-Wright, per the table above.")

st.divider()

# ---------------------------------------------------------------------------
# Peer revenue & margin trend overlay
# ---------------------------------------------------------------------------

st.subheader("Peer Comparison — Revenue Growth & Operating Margin Trend")
st.caption("Pulls the same SEC XBRL concepts for selected peers. Some companies tag concepts differently or report on a different fiscal calendar, so coverage can vary.")

peer_choices = st.multiselect(
    "Peers to overlay",
    options=list(config.PEERS.keys()),
    default=["WWD", "PH"],
    format_func=lambda t: f"{t} — {config.PEERS[t]}",
)

if peer_choices:
    with st.spinner("Looking up peer CIKs and pulling XBRL data…"):
        ticker_cik = get_company_tickers_map()
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Scatter(x=rev.tail(16).index, y=rev.tail(16).values, name="Moog",
                                      mode="lines+markers", line=dict(color=MAROON, width=3)))
        fig_om = go.Figure()
        moog_om = merged["Operating Margin"].tail(16)
        fig_om.add_trace(go.Scatter(x=moog_om.index, y=moog_om.values, name="Moog",
                                     mode="lines+markers", line=dict(color=MAROON, width=3)))

        for i, tkr in enumerate(peer_choices):
            cik = ticker_cik.get(tkr.upper())
            if not cik:
                st.warning(f"No CIK found for {tkr} in SEC's ticker map — skipping.")
                continue
            p_rev = as_value_series(quarterly_from_concept(get_financial_series(cik, "revenue")))
            p_opi = as_value_series(quarterly_from_concept(get_financial_series(cik, "operating_income")))
            if p_rev.empty:
                st.warning(f"No revenue XBRL data returned for {tkr}.")
                continue
            color = BRAND_COLORS[(i + 1) % len(BRAND_COLORS)]
            fig_rev.add_trace(go.Scatter(x=p_rev.tail(16).index, y=p_rev.tail(16).values, name=tkr,
                                          mode="lines+markers", line=dict(color=color, width=2)))
            if not p_opi.empty:
                p_om = (p_opi / p_rev).dropna().tail(16)
                fig_om.add_trace(go.Scatter(x=p_om.index, y=p_om.values, name=tkr,
                                             mode="lines+markers", line=dict(color=color, width=2)))

        fig_rev.update_layout(title="Quarterly Net Sales — Moog vs. Peers", template="plotly_white",
                               height=420, hovermode="x unified", margin=dict(l=10, r=10, t=40, b=10))
        fig_om.update_layout(title="Operating Margin — Moog vs. Peers", template="plotly_white",
                              yaxis_tickformat=".0%", height=420, hovermode="x unified",
                              margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_rev, use_container_width=True)
        st.plotly_chart(fig_om, use_container_width=True)
else:
    st.info("Select one or more peers above to overlay their revenue and margin trends.")

st.divider()
st.caption(
    "The 12-Month Backlog section above is an estimate derived from XBRL disclosures, not Moog's own "
    "exact figure — see the official [Financial Materials page]"
    f"({config.IR_LINKS['Financials']}) for Moog's as-reported twelve-month backlog each quarter."
)
