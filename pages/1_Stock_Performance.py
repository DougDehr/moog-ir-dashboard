"""Stock price performance: Moog vs. competitors and benchmarks."""

import pandas as pd
import streamlit as st

from src import config
from src.data_sources import get_price_history, get_dividends, get_fundamentals
from src.charts import (
    indexed_performance_chart, build_returns_table, annualized_volatility,
    beta_vs_benchmark, fmt_pct, bar_compare,
)
from src.theme import inject_moog_theme

st.set_page_config(page_title="Stock Performance — Moog IR Dashboard", page_icon="📈", layout="wide")
inject_moog_theme()
st.title("Stock Price Performance vs. Competitors")
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
# Short interest & liquidity
# ---------------------------------------------------------------------------

st.subheader("Short Interest & Liquidity")

with st.spinner("Pulling short interest data from Yahoo Finance…"):
    moog_short = get_fundamentals(moog_ticker)

s1, s2, s3, s4 = st.columns(4)
s1.metric("Short % of Float", fmt_pct(moog_short.get("shortPercentOfFloat")))

short_shares = moog_short.get("sharesShort")
prior_short = moog_short.get("sharesShortPriorMonth")
short_delta = None
if short_shares and prior_short:
    short_delta = f"{(short_shares / prior_short - 1) * 100:+.1f}% vs. prior month"
s2.metric("Shares Short", f"{int(short_shares):,}" if short_shares else "n/a", delta=short_delta)

short_ratio = moog_short.get("shortRatio")
s3.metric("Days to Cover", f"{short_ratio:.1f}" if short_ratio == short_ratio and short_ratio is not None else "n/a")

avg_vol = moog_short.get("averageVolume10days")
s4.metric("Avg Daily Volume (10D)", f"{int(avg_vol):,}" if avg_vol else "n/a")

if not peer_choices:
    st.info("Select competitors in the sidebar to compare short interest and liquidity.")
else:
    with st.spinner("Pulling peer short interest/liquidity data…"):
        liq_rows = [get_fundamentals(t) for t in [moog_ticker] + peer_choices]
    liq_name_map = {moog_ticker: config.COMPANY_NAME, **config.PEERS}
    liq_records = []
    for r in liq_rows:
        if "error" in r:
            continue
        liq_records.append({
            "Company": liq_name_map.get(r["ticker"], r["ticker"]),
            "Short % of Float": r.get("shortPercentOfFloat"),
            "Avg Daily Volume": r.get("averageVolume"),
        })
    liq_df = pd.DataFrame(liq_records)

    if liq_df.empty:
        st.warning("Could not retrieve peer short interest/liquidity data right now — Yahoo Finance may be rate-limiting.")
    else:
        lc1, lc2 = st.columns(2)
        with lc1:
            pdf1 = liq_df.dropna(subset=["Short % of Float"])
            if not pdf1.empty:
                fig_short = bar_compare(
                    list(pdf1["Company"]), list(pdf1["Short % of Float"]),
                    title="Short Interest (% of Float)", pct=True, highlight=config.COMPANY_NAME,
                )
                fig_short.update_layout(height=380, xaxis_tickangle=-35)
                st.plotly_chart(fig_short, use_container_width=True)
        with lc2:
            pdf2 = liq_df.dropna(subset=["Avg Daily Volume"])
            if not pdf2.empty:
                fig_vol = bar_compare(
                    list(pdf2["Company"]), list(pdf2["Avg Daily Volume"]),
                    title="Average Daily Trading Volume (Shares)", highlight=config.COMPANY_NAME,
                )
                fig_vol.update_layout(height=380, xaxis_tickangle=-35)
                st.plotly_chart(fig_vol, use_container_width=True)

        st.caption("Short interest is typically reported by exchanges twice monthly, so this figure can lag by up to ~2 weeks.")

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
