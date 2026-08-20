"""Sell-side analyst coverage: price targets, ratings, and recent rating actions
for Moog and its competitors. Source: Yahoo Finance (yfinance)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config
from src.data_sources import get_fundamentals, get_recommendations_trend, get_upgrades_downgrades
from src.charts import fmt_money, fmt_pct, bar_compare, BRAND_COLORS
from src.theme import inject_moog_theme, MAROON

st.set_page_config(page_title="Analyst Coverage — Moog IR Dashboard", page_icon="📊", layout="wide")
inject_moog_theme()
st.title("Analyst Coverage")
st.caption(
    "Sell-side price targets, consensus ratings, and recent rating actions. Source: Yahoo Finance "
    "(yfinance) — vendor-aggregated analyst data that can lag the sell-side desks' own publications "
    "by a few days."
)

RECS = ["strongBuy", "buy", "hold", "sell", "strongSell"]
REC_LABELS = {"strongBuy": "Strong Buy", "buy": "Buy", "hold": "Hold", "sell": "Sell", "strongSell": "Strong Sell"}
REC_COLORS = {"strongBuy": "#1B7F79", "buy": "#4C7A4C", "hold": "#C98A2B", "sell": "#B0512A", "strongSell": "#87212E"}
PERIOD_LABELS = {"0m": "Current", "-1m": "1 Mo. Ago", "-2m": "2 Mo. Ago", "-3m": "3 Mo. Ago"}


def _rec_label(key):
    if not key or key != key:
        return "n/a"
    return key.replace("_", " ").title()


def _upside(current, target):
    if current in (None,) or target in (None,) or current != current or target != target or current == 0:
        return None
    return target / current - 1


with st.sidebar:
    st.header("Coverage Controls")
    moog_class = st.radio("Moog share class", list(config.SHARE_CLASSES.keys()), index=0)
    peer_choices = st.multiselect(
        "Competitors to include",
        options=list(config.PEERS.keys()),
        default=list(config.PEERS.keys()),
        format_func=lambda t: f"{t} — {config.PEERS[t]}",
    )

moog_ticker = config.SHARE_CLASSES[moog_class]

# ---------------------------------------------------------------------------
# Moog — price targets & consensus
# ---------------------------------------------------------------------------

st.subheader(f"Moog Inc. — {moog_class}")

with st.spinner("Pulling analyst data from Yahoo Finance…"):
    moog_f = get_fundamentals(moog_ticker)

if "error" in moog_f or moog_f.get("currentPrice") is None:
    st.warning("Could not retrieve analyst data for Moog right now — Yahoo Finance may be rate-limiting. Try again shortly.")
else:
    current = moog_f["currentPrice"]
    mean_t = moog_f["targetMeanPrice"]
    upside = _upside(current, mean_t)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Price", fmt_money(current))
    m2.metric("Mean Target", fmt_money(mean_t))
    m3.metric("Implied Upside/Downside", fmt_pct(upside) if upside is not None else "n/a")
    m4.metric("# Analysts", f"{int(moog_f['numberOfAnalystOpinions'])}" if moog_f.get("numberOfAnalystOpinions") else "n/a")
    m5.metric("Consensus Rating", _rec_label(moog_f.get("recommendationKey")))

    # Price target range chart: low – mean/median – high, with current price marker
    lo, hi, med = moog_f.get("targetLowPrice"), moog_f.get("targetHighPrice"), moog_f.get("targetMedianPrice")
    if lo is not None and hi is not None:
        fig_range = go.Figure()
        fig_range.add_trace(go.Bar(
            x=[hi - lo], y=["Price Target Range"], base=[lo], orientation="h",
            marker_color="#F3E4E6", marker_line_color=MAROON, marker_line_width=1,
            name="Low–High Range", showlegend=False, width=0.4,
        ))
        markers = [
            ("Current Price", current, "#25292B", "circle"),
            ("Mean Target", mean_t, MAROON, "diamond"),
            ("Median Target", med, "#2E4057", "diamond"),
        ]
        for label, val, color, symbol in markers:
            if val is None or val != val:
                continue
            fig_range.add_trace(go.Scatter(
                x=[val], y=["Price Target Range"], mode="markers",
                marker=dict(size=16, color=color, symbol=symbol, line=dict(width=1, color="white")),
                name=f"{label}: {fmt_money(val)}",
            ))
        fig_range.update_layout(
            template="plotly_white", height=220,
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
            margin=dict(l=10, r=10, t=20, b=70),
            xaxis_title="USD per share",
        )
        st.plotly_chart(fig_range, use_container_width=True)

    # Recommendation trend
    rec_trend = get_recommendations_trend(moog_ticker)
    if not rec_trend.empty and "period" in rec_trend.columns:
        order = ["-3m", "-2m", "-1m", "0m"]
        rt = rec_trend.set_index("period").reindex([p for p in order if p in rec_trend["period"].values])
        fig_trend = go.Figure()
        for key in RECS:
            if key not in rt.columns:
                continue
            fig_trend.add_trace(go.Bar(
                x=[PERIOD_LABELS.get(p, p) for p in rt.index], y=rt[key],
                name=REC_LABELS[key], marker_color=REC_COLORS[key],
            ))
        fig_trend.update_layout(
            barmode="stack", title="Recommendation Trend (# of Analysts)",
            template="plotly_white", height=380,
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
            margin=dict(l=10, r=10, t=40, b=70),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No recommendation-trend history returned for this ticker.")

    # Recent rating actions
    st.markdown("**Recent Analyst Rating Actions**")
    ud = get_upgrades_downgrades(moog_ticker, limit=15)
    if ud.empty:
        st.info("No recent rating actions returned for this ticker.")
    else:
        blank = pd.Series([""] * len(ud), index=ud.index)
        from_grade = ud["FromGrade"] if "FromGrade" in ud.columns else blank
        to_grade = ud["ToGrade"] if "ToGrade" in ud.columns else blank
        ud_display = pd.DataFrame({
            "Date": ud["GradeDate"].dt.date if "GradeDate" in ud.columns else None,
            "Firm": ud.get("Firm"),
            "Action": ud.get("Action"),
            "From → To": from_grade.fillna("").astype(str) + " → " + to_grade.fillna("").astype(str),
            "Price Target": (ud["currentPriceTarget"].apply(lambda v: fmt_money(v) if v else "—")
                              if "currentPriceTarget" in ud.columns else None),
        })
        st.dataframe(ud_display, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Peer analyst coverage comparison
# ---------------------------------------------------------------------------

st.subheader("Analyst Coverage — Moog vs. Competitors")

if not peer_choices:
    st.info("Select at least one competitor in the sidebar to compare analyst coverage.")
else:
    tickers = [moog_ticker] + peer_choices
    with st.spinner("Pulling peer analyst data from Yahoo Finance…"):
        rows = [get_fundamentals(t) for t in tickers]

    name_map = {moog_ticker: config.COMPANY_NAME, **config.PEERS}
    records = []
    for r in rows:
        if "error" in r:
            continue
        records.append({
            "Ticker": r["ticker"],
            "Company": name_map.get(r["ticker"], r["ticker"]),
            "Current Price": r.get("currentPrice"),
            "Mean Target": r.get("targetMeanPrice"),
            "Upside/Downside": _upside(r.get("currentPrice"), r.get("targetMeanPrice")),
            "# Analysts": r.get("numberOfAnalystOpinions"),
            "Consensus": _rec_label(r.get("recommendationKey")),
        })
    peer_df = pd.DataFrame(records)

    if peer_df.empty:
        st.warning("Could not retrieve peer analyst data right now — Yahoo Finance may be rate-limiting.")
    else:
        display_df = peer_df.copy()
        display_df["Current Price"] = display_df["Current Price"].apply(fmt_money)
        display_df["Mean Target"] = display_df["Mean Target"].apply(fmt_money)
        display_df["Upside/Downside"] = display_df["Upside/Downside"].apply(lambda v: fmt_pct(v) if v is not None else "n/a")
        display_df["# Analysts"] = display_df["# Analysts"].apply(lambda v: int(v) if v == v and v is not None else "n/a")
        st.dataframe(display_df.drop(columns=["Ticker"]), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            plot_df = peer_df.dropna(subset=["Upside/Downside"])
            if not plot_df.empty:
                fig_up = bar_compare(
                    list(plot_df["Company"]), list(plot_df["Upside/Downside"]),
                    title="Implied Upside/Downside to Mean Target", pct=True, highlight=config.COMPANY_NAME,
                )
                fig_up.update_layout(height=400, xaxis_tickangle=-35)
                st.plotly_chart(fig_up, use_container_width=True)
        with c2:
            plot_df2 = peer_df.dropna(subset=["# Analysts"])
            if not plot_df2.empty:
                fig_cov = bar_compare(
                    list(plot_df2["Company"]), list(plot_df2["# Analysts"]),
                    title="Number of Covering Analysts", highlight=config.COMPANY_NAME,
                )
                fig_cov.update_layout(height=400, xaxis_tickangle=-35)
                st.plotly_chart(fig_cov, use_container_width=True)

        st.caption(
            "Consensus rating and price targets are vendor-aggregated from sell-side analyst estimates "
            "and can differ from any single firm's published view."
        )
