"""Institutional ownership and insider (Form 4) activity for Moog and its competitors."""

import pandas as pd
import streamlit as st

from src import config
from src.data_sources import (
    get_fundamentals, get_major_holders_breakdown, get_institutional_holders, get_insider_transactions,
)
from src.charts import fmt_money, fmt_pct, bar_compare
from src.theme import inject_moog_theme
from src.ui import external_data_unavailable

st.set_page_config(page_title="Ownership — Moog IR Dashboard", page_icon="🏛️", layout="wide")
inject_moog_theme()
st.title("Ownership & Insider Activity")
st.caption(
    "Institutional holders and Form 4 insider transactions, as aggregated by Yahoo Finance from 13F and "
    "Form 3/4/5 filings. Holdings data typically lags the actual filing by several weeks."
)

with st.sidebar:
    st.header("Ownership Controls")
    moog_class = st.radio("Moog share class", list(config.SHARE_CLASSES.keys()), index=0)
    peer_choices = st.multiselect(
        "Competitors to include",
        options=list(config.PEERS.keys()),
        default=list(config.PEERS.keys()),
        format_func=lambda t: f"{t} — {config.PEERS[t]}",
    )

moog_ticker = config.SHARE_CLASSES[moog_class]

# ---------------------------------------------------------------------------
# Moog ownership snapshot
# ---------------------------------------------------------------------------

st.subheader(f"Moog Inc. — {moog_class}")

with st.spinner("Pulling ownership data from Yahoo Finance…"):
    moog_f = get_fundamentals(moog_ticker)
    holders_breakdown = get_major_holders_breakdown(moog_ticker)
    inst_holders = get_institutional_holders(moog_ticker, limit=10)
    insider_tx = get_insider_transactions(moog_ticker, limit=20)

if "error" in moog_f:
    external_data_unavailable("ownership data for Moog", level="warning")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Institutional Ownership", fmt_pct(moog_f.get("heldPercentInstitutions")))
m2.metric("Insider Ownership", fmt_pct(moog_f.get("heldPercentInsiders")))
inst_count = holders_breakdown.get("institutionsCount")
m3.metric("# Institutional Holders", f"{int(inst_count):,}" if inst_count == inst_count and inst_count else "n/a")
m4.metric("Float Shares", f"{int(moog_f['floatShares']):,}" if moog_f.get("floatShares") else "n/a")

st.markdown("**Top Institutional Holders**")
if inst_holders.empty:
    st.info("No institutional holder data returned for this ticker.")
else:
    disp = pd.DataFrame({
        "Holder": inst_holders["Holder"],
        "Date Reported": pd.to_datetime(inst_holders["Date Reported"]).dt.date,
        "% Held": inst_holders["pctHeld"].apply(lambda v: fmt_pct(v)),
        "Shares": inst_holders["Shares"].apply(lambda v: f"{int(v):,}" if v == v else "n/a"),
        "Value": inst_holders["Value"].apply(fmt_money),
        "QoQ Change": inst_holders["pctChange"].apply(lambda v: fmt_pct(v) if v == v else "n/a"),
    })
    st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("**Recent Insider Transactions (Form 4)**")
if insider_tx.empty:
    st.info("No insider transaction data returned for this ticker.")
else:
    sales = insider_tx.loc[insider_tx["Action"] == "Sale", "Value"].sum()
    purchases = insider_tx.loc[insider_tx["Action"] == "Purchase", "Value"].sum()
    net = purchases - sales
    # NOTE: Streamlit's markdown renderer treats matched pairs of "$" as inline LaTeX,
    # so two or more dollar-amount strings in one st.caption/markdown call must have
    # their "$" escaped as "\$" or the text garbles (each fmt_money() output starts
    # with "$"; three-plus of them in one call reliably triggers this).
    fmt_money_md = lambda v: fmt_money(v).replace("$", "\\$")
    st.caption(
        f"Across the {len(insider_tx)} most recent filed transactions shown below: "
        f"**{fmt_money_md(purchases)}** in open-market purchases vs. **{fmt_money_md(sales)}** in open-market "
        f"sales — net {fmt_money_md(net)}. Gifts, awards, and option exercises are excluded from this net figure."
    )
    disp_tx = pd.DataFrame({
        "Date": pd.to_datetime(insider_tx["Start Date"]).dt.date,
        "Insider": insider_tx["Insider"],
        "Position": insider_tx.get("Position"),
        "Action": insider_tx["Action"],
        "Shares": insider_tx["Shares"].apply(lambda v: f"{int(v):,}" if v == v else "n/a"),
        "Value": insider_tx["Value"].apply(lambda v: fmt_money(v) if v else "—"),
        "Detail": insider_tx.get("Text"),
    })
    st.dataframe(disp_tx, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Peer ownership comparison
# ---------------------------------------------------------------------------

st.subheader("Ownership — Moog vs. Competitors")

if not peer_choices:
    st.info("Select at least one competitor in the sidebar to compare ownership structure.")
else:
    tickers = [moog_ticker] + peer_choices
    name_map = {moog_ticker: config.COMPANY_NAME, **config.PEERS}
    with st.spinner("Pulling peer ownership data from Yahoo Finance…"):
        rows = [get_fundamentals(t) for t in tickers]

    records = []
    for r in rows:
        if "error" in r:
            continue
        records.append({
            "Company": name_map.get(r["ticker"], r["ticker"]),
            "Institutional Ownership": r.get("heldPercentInstitutions"),
            "Insider Ownership": r.get("heldPercentInsiders"),
        })
    own_df = pd.DataFrame(records)

    if own_df.empty:
        external_data_unavailable("peer ownership data", level="warning")
    else:
        c1, c2 = st.columns(2)
        with c1:
            plot_df = own_df.dropna(subset=["Institutional Ownership"])
            if not plot_df.empty:
                fig1 = bar_compare(
                    list(plot_df["Company"]), list(plot_df["Institutional Ownership"]),
                    title="Institutional Ownership", pct=True, highlight=config.COMPANY_NAME,
                )
                fig1.update_layout(height=400, xaxis_tickangle=-35)
                st.plotly_chart(fig1, use_container_width=True)
        with c2:
            plot_df2 = own_df.dropna(subset=["Insider Ownership"])
            if not plot_df2.empty:
                fig2 = bar_compare(
                    list(plot_df2["Company"]), list(plot_df2["Insider Ownership"]),
                    title="Insider Ownership", pct=True, highlight=config.COMPANY_NAME,
                )
                fig2.update_layout(height=400, xaxis_tickangle=-35)
                st.plotly_chart(fig2, use_container_width=True)

        st.caption(
            "Institutional/insider ownership % as reported by Yahoo Finance's vendor aggregation; can vary "
            "slightly from figures calculated directly off 13F/Form 4 filings depending on reporting-date cutoffs."
        )
