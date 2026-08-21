"""Competitor / peer valuation and margin comparison."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config
from src.data_sources import get_fundamentals
from src.charts import fmt_money, fmt_pct, fmt_ratio, bar_compare, BRAND_COLORS
from src.theme import inject_moog_theme, MAROON
from src.ui import external_data_unavailable

st.set_page_config(page_title="Competitor Analysis — Moog IR Dashboard", page_icon="⚖️", layout="wide")
inject_moog_theme()
st.title("Competitor Analysis")
st.caption(
    "Peer set: aerospace & defense / precision-motion-control companies commonly used as Moog's "
    "public-market comparables — flight-control actuation, motion control, and aerospace "
    "component suppliers of comparable or adjacent scale. Source: Yahoo Finance fundamentals."
)

with st.sidebar:
    st.header("Peer Selection")
    peer_choices = st.multiselect(
        "Competitors to include",
        options=list(config.PEERS.keys()),
        default=list(config.PEERS.keys()),
        format_func=lambda t: f"{t} — {config.PEERS[t]}",
    )
    moog_class = st.radio("Moog share class for fundamentals", list(config.SHARE_CLASSES.keys()), index=0)

moog_ticker = config.SHARE_CLASSES[moog_class]
tickers = [moog_ticker] + peer_choices

with st.spinner("Pulling fundamentals from Yahoo Finance…"):
    rows = [get_fundamentals(t) for t in tickers]

df = pd.DataFrame(rows).set_index("ticker")
name_map = {moog_ticker: config.COMPANY_NAME, **config.PEERS}
df["Company"] = [name_map.get(t, t) for t in df.index]

if "error" in df.columns and df["error"].notna().all():
    external_data_unavailable("fundamentals for the selected companies")
    st.stop()

# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------

st.subheader("Valuation & Profitability Comparison")

table = pd.DataFrame({
    "Company": df["Company"],
    "Market Cap": df["marketCap"].apply(fmt_money),
    "P/E (TTM)": df["trailingPE"].apply(fmt_ratio),
    "Fwd P/E": df["forwardPE"].apply(fmt_ratio),
    "EV/EBITDA": df["enterpriseToEbitda"].apply(fmt_ratio),
    "Revenue (TTM)": df["totalRevenue"].apply(fmt_money),
    "Rev. Growth YoY": df["revenueGrowth"].apply(fmt_pct),
    "Gross Margin": df["grossMargins"].apply(fmt_pct),
    "Operating Margin": df["operatingMargins"].apply(fmt_pct),
    "Net Margin": df["profitMargins"].apply(fmt_pct),
    "Dividend Yield": df["dividendYield"].apply(lambda v: fmt_pct(v) if v and v == v and v < 1 else (f"{v:.2f}%" if v == v else "n/a")),
})
st.dataframe(table, use_container_width=True, hide_index=True)
st.caption("P/E, margins and growth are trailing/forward figures as reported by the data vendor and can lag actual filings by a few weeks.")

st.divider()

# ---------------------------------------------------------------------------
# Margin bar charts
# ---------------------------------------------------------------------------

st.subheader("Margin Comparison")
mcols = st.columns(3)
metric_specs = [
    ("Gross Margin", "grossMargins"),
    ("Operating Margin", "operatingMargins"),
    ("Net Margin", "profitMargins"),
]
for col, (title, key) in zip(mcols, metric_specs):
    with col:
        cats = list(df["Company"])
        vals = list(df[key])
        fig = bar_compare(cats, vals, title=title, pct=True, highlight=config.COMPANY_NAME)
        fig.update_layout(height=380, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Growth vs. profitability scatter (bubble = market cap)
# ---------------------------------------------------------------------------

st.subheader("Revenue Growth vs. Operating Margin")
scatter_df = df.dropna(subset=["revenueGrowth", "operatingMargins"]).copy()
if not scatter_df.empty:
    sizes = scatter_df["marketCap"].fillna(scatter_df["marketCap"].median())
    fig2 = go.Figure()
    for i, (tkr, row) in enumerate(scatter_df.iterrows()):
        is_moog = tkr == moog_ticker
        fig2.add_trace(go.Scatter(
            x=[row["revenueGrowth"]], y=[row["operatingMargins"]],
            mode="markers+text",
            marker=dict(
                size=max(20, min(70, (sizes.loc[tkr] / sizes.max()) * 70)),
                color=MAROON if is_moog else BRAND_COLORS[i % len(BRAND_COLORS)],
                opacity=0.85,
            ),
            text=[row["Company"]],
            textposition="top center",
            name=row["Company"],
            showlegend=False,
        ))
    fig2.update_layout(
        xaxis_title="Revenue Growth YoY", yaxis_title="Operating Margin",
        xaxis_tickformat=".0%", yaxis_tickformat=".0%",
        template="plotly_white", height=520,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Bubble size ≈ market capitalization. Moog highlighted in maroon.")
else:
    st.info("Not enough vendor data returned to plot growth vs. margin for the selected peers.")

st.divider()

# ---------------------------------------------------------------------------
# Radar: Moog vs peer average (normalized)
# ---------------------------------------------------------------------------

st.subheader("Moog vs. Peer Average — Normalized Profile")
radar_metrics = {
    "Gross Margin": "grossMargins",
    "Operating Margin": "operatingMargins",
    "Net Margin": "profitMargins",
    "Revenue Growth": "revenueGrowth",
    "Dividend Yield": "dividendYield",
}
peer_only = df.drop(index=moog_ticker, errors="ignore")
if moog_ticker in df.index and not peer_only.empty:
    moog_row = df.loc[moog_ticker]
    cats = list(radar_metrics.keys())
    moog_vals, peer_vals = [], []
    for label, key in radar_metrics.items():
        col_vals = df[key].dropna()
        if col_vals.empty or col_vals.max() == col_vals.min():
            moog_vals.append(0)
            peer_vals.append(0)
            continue
        lo, hi = col_vals.min(), col_vals.max()
        norm = lambda v: (v - lo) / (hi - lo) if v == v else 0
        moog_vals.append(norm(moog_row[key]))
        peer_vals.append(norm(peer_only[key].mean()))

    fig3 = go.Figure()
    fig3.add_trace(go.Scatterpolar(r=moog_vals + moog_vals[:1], theta=cats + cats[:1],
                                    fill="toself", name="Moog", line_color=MAROON))
    fig3.add_trace(go.Scatterpolar(r=peer_vals + peer_vals[:1], theta=cats + cats[:1],
                                    fill="toself", name="Peer Average", line_color="#2E4057", opacity=0.6))
    fig3.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1], showticklabels=False)),
        showlegend=True, template="plotly_white", height=500,
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Each axis min-max normalized across the selected peer set (0 = lowest, 1 = highest in the group) — shape shows relative positioning, not absolute values.")
else:
    st.info("Select at least one competitor to compare against Moog.")
