"""Shared Plotly chart builders and small formatting helpers used across pages."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Moog's actual brand maroon leads the palette so Moog's own series reads
# consistently across every chart (sampled from moog.com/investors.html).
BRAND_COLORS = [
    "#87212E",  # Moog maroon
    "#2E4057",  # slate navy
    "#1B7F79",  # teal
    "#C98A2B",  # gold
    "#5C6BC0",  # indigo
    "#4C7A4C",  # green
    "#8C6A4E",  # brown
    "#6C6C6C",  # neutral gray
]


def fmt_money(x, suffix=""):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    ax = abs(x)
    if ax >= 1e12:
        s = f"${x/1e12:,.2f}T"
    elif ax >= 1e9:
        s = f"${x/1e9:,.2f}B"
    elif ax >= 1e6:
        s = f"${x/1e6:,.1f}M"
    else:
        s = f"${x:,.0f}"
    return s + suffix


def fmt_pct(x, digits=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x * 100:,.{digits}f}%"


def fmt_ratio(x, digits=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{digits}f}x"


def normalize_to_100(price_df: pd.DataFrame) -> pd.DataFrame:
    """Rebase each column to start at 100 on its own first valid value.

    Deliberately avoids any label-based .loc[timestamp] lookup — pulling a
    'first valid index' label from one derived Series and then looking it
    up again in another is exactly the kind of thing that breaks across
    pandas versions/edge cases (duplicate index entries, tz handling,
    dtype quirks) for no benefit here. .iloc[0] on a dropna'd column and a
    single vectorized column-aligned divide can't raise a KeyError.
    """
    if price_df.empty:
        return price_df
    df = price_df.dropna(how="all")

    def _first_valid_value(s: pd.Series):
        s = s.dropna()
        return s.iloc[0] if not s.empty else np.nan

    bases = df.apply(_first_valid_value)
    usable = bases[bases.notna() & (bases != 0)].index
    if len(usable) == 0:
        return pd.DataFrame(index=df.index)
    return df[usable].divide(bases[usable], axis=1) * 100


def indexed_performance_chart(price_df: pd.DataFrame, title: str = "Indexed Price Performance (Rebased to 100)") -> go.Figure:
    idx_df = normalize_to_100(price_df)
    fig = go.Figure()
    for i, col in enumerate(idx_df.columns):
        fig.add_trace(go.Scatter(
            x=idx_df.index, y=idx_df[col],
            mode="lines", name=col,
            line=dict(width=2.5, color=BRAND_COLORS[i % len(BRAND_COLORS)]),
        ))
    fig.update_layout(
        title=title,
        xaxis_title=None,
        yaxis_title="Indexed value (start = 100)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=60, b=90),
        template="plotly_white",
    )
    return fig


def period_return(price_series: pd.Series, days: int) -> float:
    s = price_series.dropna()
    if s.empty:
        return np.nan
    end_val = s.iloc[-1]
    cutoff = s.index[-1] - pd.Timedelta(days=days)
    prior = s[s.index <= cutoff]
    if prior.empty:
        return np.nan
    start_val = prior.iloc[-1]
    if start_val == 0 or np.isnan(start_val):
        return np.nan
    return end_val / start_val - 1


def ytd_return(price_series: pd.Series) -> float:
    s = price_series.dropna()
    if s.empty:
        return np.nan
    year_start = pd.Timestamp(year=s.index[-1].year, month=1, day=1)
    prior = s[s.index <= year_start]
    base = prior.iloc[-1] if not prior.empty else s.iloc[0]
    if base == 0 or np.isnan(base):
        return np.nan
    return s.iloc[-1] / base - 1


def build_returns_table(price_df: pd.DataFrame, name_map: dict[str, str] | None = None) -> pd.DataFrame:
    rows = []
    for col in price_df.columns:
        s = price_df[col]
        rows.append({
            "Ticker": col,
            "Name": (name_map or {}).get(col, col),
            "1M": period_return(s, 30),
            "3M": period_return(s, 91),
            "6M": period_return(s, 182),
            "YTD": ytd_return(s),
            "1Y": period_return(s, 365),
            "3Y": period_return(s, 365 * 3),
            "5Y": period_return(s, 365 * 5),
        })
    return pd.DataFrame(rows).set_index("Ticker")


def annualized_volatility(price_df: pd.DataFrame, window_days: int = 365) -> pd.Series:
    rets = price_df.pct_change()
    cutoff = price_df.index[-1] - pd.Timedelta(days=window_days)
    rets = rets[rets.index >= cutoff]
    return rets.std() * np.sqrt(252)


def beta_vs_benchmark(price_df: pd.DataFrame, benchmark_col: str, window_days: int = 365 * 3) -> pd.Series:
    rets = price_df.pct_change().dropna(how="all")
    cutoff = rets.index[-1] - pd.Timedelta(days=window_days) if not rets.empty else None
    if cutoff is not None:
        rets = rets[rets.index >= cutoff]
    if benchmark_col not in rets.columns:
        return pd.Series(dtype=float)
    bench = rets[benchmark_col]
    out = {}
    for col in rets.columns:
        if col == benchmark_col:
            continue
        joined = pd.concat([rets[col], bench], axis=1).dropna()
        if len(joined) < 30 or joined.iloc[:, 1].var() == 0:
            out[col] = np.nan
            continue
        cov = joined.cov().iloc[0, 1]
        var = joined.iloc[:, 1].var()
        out[col] = cov / var
    return pd.Series(out)


def bar_compare(categories: list[str], values: list[float], title: str, y_title: str = "",
                 highlight: str | None = None, pct=False) -> go.Figure:
    colors = []
    for c in categories:
        colors.append(BRAND_COLORS[0] if c == highlight else "#2E4057")
    text = [f"{v*100:.1f}%" if pct and v == v else (f"{v:.1f}" if v == v else "n/a") for v in values]
    fig = go.Figure(go.Bar(x=categories, y=values, marker_color=colors, text=text, textposition="outside"))
    fig.update_layout(
        title=title, yaxis_title=y_title, template="plotly_white",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    if pct:
        fig.update_yaxes(tickformat=".0%")
    return fig
