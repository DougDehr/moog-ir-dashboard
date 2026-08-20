"""Stock price performance: Moog vs. competitors and benchmarks."""

import pandas as pd
import streamlit as st

from src import config
from src.data_sources import get_price_history, get_dividends
from src.charts import (
    indexed_performance_chart, build_returns_table, annualized_volatility,
    beta_vs_benchmark, fmt_pct,
)
from src.theme import inject_moog_theme

st.set_page_config(page_title="Stock Performance — Moog IR Dashboard", page_icon="📈", layout="wide")
inject_moog_theme()
st.title("📈 Stock Price Performance vs. Competitors")
st.caption("Source: Yahoo Finance (yfinance), adjusted close. Indexed charts rebase every series to 100 at the start of the selected window.")

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Chart Controls")
    moog_class = st.radio("Moog share class", list(config.SHARE_CLASSES.keys()), index=0)
    moog_ticker = config.SHARE_CLASSES[moog_class]

    peer_choices = st.multiselect(
        "Competitors",
        options=list(config.PEERS.keys()),
        default=["WWD", "PH", "TDG", "CW", "HEI"],
        format_func=lambda t: f"{t} — {config.PEERS[t]}",
    )

    bench_choices = st.multiselect(
        "Benchmarks",
        options=list(config.BENCHMARKS.keys()),
        default=["S&P 500 (^GSPC)", "Aerospace & Defense ETF (ITA)"],
    )

    period = st.select_slider(
        "Lookback window",
        options=["6mo", "1y", "2y", "3y", "5y", "10y", "max"],
        value="3y",
    )

tickers = [moog_ticker] + peer_choices + [config.BENCHMARKS[b] for b in bench_choices]
tickers = list(dict.fromkeys(tickers))  # de-dupe, keep order

name_map = {moog_ticker: f"Moog ({moog_class})"}
name_map.update(config.PEERS)
name_map.update({v: k for k, v in config.BENCHMARKS.items()})

with st.spinner("Pulling price history from Yahoo Finance…"):
    prices = get_price_history(tuple(tickers), period=period)

if prices.empty:
    st.error("Could not retrieve price data right now. Yahoo Finance may be rate-limiting — try again shortly.")
    st.stop()

# ---------------------------------------------------------------------------
# Indexed performance chart
# ---------------------------------------------------------------------------

display_df = prices.rename(columns=name_map)
fig = indexed_performance_chart(display_df, title=f"Indexed Price Performance — {period} lookback")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Returns table
# ---------------------------------------------------------------------------

st.subheader("Trailing Returns")
returns_df = build_returns_table(prices, name_map)
pct_cols = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]
styled = returns_df.copy()
for c in pct_cols:
    styled[c] = styled[c].apply(lambda v: fmt_pct(v) if v == v else "n/a")
st.dataframe(styled, use_container_width=True)
st.caption("Total price return (not dividend-adjusted total return). Periods with insufficient history show 'n/a'.")

st.divider()

# ---------------------------------------------------------------------------
# Risk metrics: volatility + beta
# ---------------------------------------------------------------------------

st.subheader("Volatility & Beta")
c1, c2 = st.columns(2)

with c1:
    st.markdown("**Annualized Volatility (trailing 1Y, daily returns)**")
    vol = annualized_volatility(prices, window_days=365).rename(index=name_map)
    st.dataframe(vol.apply(lambda v: fmt_pct(v)).rename("Ann. Volatility"), use_container_width=True)

with c2:
    bench_for_beta = None
    for b in bench_choices:
        if config.BENCHMARKS[b] == "^GSPC":
            bench_for_beta = "^GSPC"
            break
    if bench_for_beta and bench_for_beta in prices.columns:
        st.markdown("**Beta vs. S&P 500 (trailing 3Y, daily returns)**")
        beta = beta_vs_benchmark(prices, bench_for_beta, window_days=365 * 3).rename(index=name_map)
        st.dataframe(beta.apply(lambda v: f"{v:.2f}" if v == v else "n/a").rename("Beta"), use_container_width=True)
    else:
        st.info("Add the S&P 500 benchmark in the sidebar to compute beta.")

st.divider()

# ---------------------------------------------------------------------------
# Dividends (Moog)
# ---------------------------------------------------------------------------

st.subheader(f"Dividend History — {moog_class}")
div = get_dividends(moog_ticker, period="5y")
if div.empty:
    st.info("No dividend data returned for this ticker/window.")
else:
    st.bar_chart(div)
    st.caption(f"Trailing 12-month dividends paid: ${div[div.index >= div.index.max() - pd.Timedelta(days=365)].sum():.2f}/share")
