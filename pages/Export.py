"""Generate a one-page PDF snapshot (market, financials, analyst, ownership, peer
comparison) for board decks or management briefings."""

import datetime as dt

import pandas as pd
import streamlit as st

from src import config
from src.data_sources import get_quote, get_financial_series, quarterly_from_concept, get_fundamentals
from src.charts import fmt_money, fmt_pct, fmt_ratio
from src.theme import inject_moog_theme
from src.report import build_one_pager

st.set_page_config(page_title="Export — Moog IR Dashboard", page_icon="🖨️", layout="wide")
inject_moog_theme()
st.title("Export One-Pager")
st.caption(
    "Generates a single-page PDF snapshot — market data, latest-quarter financials, analyst coverage, "
    "ownership, and a peer comparison table — for board decks or management briefings. Pulls fresh data "
    "each time you click Generate."
)

with st.sidebar:
    st.header("Export Controls")
    peer_choices = st.multiselect(
        "Peers to include in comparison table",
        options=list(config.PEERS.keys()),
        default=list(config.PEERS.keys()),
        format_func=lambda t: f"{t} — {config.PEERS[t]}",
    )


def _rec_label(key):
    if not key or key != key:
        return "n/a"
    return key.replace("_", " ").title()


def _upside(current, target):
    if not current or not target or current != current or target != target or current == 0:
        return None
    return target / current - 1


if st.button("Generate One-Pager", type="primary"):
    with st.spinner("Gathering latest data from Yahoo Finance and SEC EDGAR…"):
        # Market snapshot
        share_classes = []
        for label, ticker in config.SHARE_CLASSES.items():
            q = get_quote(ticker)
            price = f"${q['last_price']:,.2f}" if q.get("last_price") == q.get("last_price") else "n/a"
            share_classes.append({"label": label, "price": price})

        moog_a = get_fundamentals(config.PRIMARY_TICKER)
        market_cap = fmt_money(moog_a.get("marketCap"))
        week_range = (
            f"${moog_a['fiftyTwoWeekLow']:,.0f}–${moog_a['fiftyTwoWeekHigh']:,.0f}"
            if moog_a.get("fiftyTwoWeekLow") and moog_a.get("fiftyTwoWeekHigh") else "n/a"
        )

        # Latest quarter (SEC XBRL)
        rev_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "revenue"))
        opinc_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "operating_income"))
        ni_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "net_income"))
        eps_df = quarterly_from_concept(get_financial_series(config.COMPANY_CIK, "diluted_eps"))

        def _latest_two(df):
            if df.empty:
                return None, None
            latest = df.iloc[-1]
            py = df[df["end"] <= latest["end"] - pd.DateOffset(months=11)]
            return latest, (py.iloc[-1] if not py.empty else None)

        rev_latest, rev_py = _latest_two(rev_df)
        op_latest, _ = _latest_two(opinc_df)
        ni_latest, ni_py = _latest_two(ni_df)
        eps_latest, _ = _latest_two(eps_df)

        quarter_label = f"Qtr ended {rev_latest['end'].date()}" if rev_latest is not None else "n/a"
        net_sales = fmt_money(rev_latest["val"]) if rev_latest is not None else "n/a"
        net_sales_yoy = (
            f"{'+' if rev_latest['val'] >= rev_py['val'] else ''}{fmt_pct(rev_latest['val'] / rev_py['val'] - 1)} YoY"
            if rev_latest is not None and rev_py is not None and rev_py["val"] else ""
        )
        op_margin = (
            fmt_pct(op_latest["val"] / rev_latest["val"])
            if op_latest is not None and rev_latest is not None and rev_latest["val"] else "n/a"
        )
        net_income = fmt_money(ni_latest["val"]) if ni_latest is not None else "n/a"
        net_income_yoy = (
            f"{'+' if ni_latest['val'] >= ni_py['val'] else ''}{fmt_pct(ni_latest['val'] / ni_py['val'] - 1)} YoY"
            if ni_latest is not None and ni_py is not None and ni_py["val"] else ""
        )
        diluted_eps = f"${eps_latest['val']:.2f}" if eps_latest is not None else "n/a"

        # Analyst + ownership + short interest (Moog)
        upside = _upside(moog_a.get("currentPrice"), moog_a.get("targetMeanPrice"))
        analyst = {
            "mean_target": fmt_money(moog_a.get("targetMeanPrice")),
            "upside": fmt_pct(upside) if upside is not None else "n/a",
            "num_analysts": str(int(moog_a["numberOfAnalystOpinions"])) if moog_a.get("numberOfAnalystOpinions") else "n/a",
            "consensus": _rec_label(moog_a.get("recommendationKey")),
        }
        ownership = {
            "institutional": fmt_pct(moog_a.get("heldPercentInstitutions")),
            "insider": fmt_pct(moog_a.get("heldPercentInsiders")),
        }
        short_interest = {
            "short_pct_float": fmt_pct(moog_a.get("shortPercentOfFloat")),
            "days_to_cover": f"{moog_a['shortRatio']:.1f}" if moog_a.get("shortRatio") else "n/a",
        }

        # Peer comparison table
        peer_headers = ["Company", "Mkt Cap", "P/E (TTM)", "Rev Growth", "Op Margin", "Upside", "# Analysts", "Inst. Own."]
        peer_rows = []
        name_map = {config.PRIMARY_TICKER: config.COMPANY_NAME, **config.PEERS}
        for t in [config.PRIMARY_TICKER] + peer_choices:
            f = get_fundamentals(t)
            if "error" in f:
                continue
            up = _upside(f.get("currentPrice"), f.get("targetMeanPrice"))
            peer_rows.append([
                name_map.get(t, t),
                fmt_money(f.get("marketCap")),
                fmt_ratio(f.get("trailingPE")),
                fmt_pct(f.get("revenueGrowth")),
                fmt_pct(f.get("operatingMargins")),
                fmt_pct(up) if up is not None else "n/a",
                str(int(f["numberOfAnalystOpinions"])) if f.get("numberOfAnalystOpinions") else "n/a",
                fmt_pct(f.get("heldPercentInstitutions")),
            ])

        pdf_bytes = build_one_pager(
            generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            share_classes=share_classes,
            market_cap=market_cap,
            week_range=week_range,
            quarter_label=quarter_label,
            net_sales=net_sales,
            net_sales_yoy=net_sales_yoy,
            op_margin=op_margin,
            net_income=net_income,
            net_income_yoy=net_income_yoy,
            diluted_eps=diluted_eps,
            analyst=analyst,
            ownership=ownership,
            short_interest=short_interest,
            peer_rows=peer_rows,
            peer_headers=peer_headers,
        )

    st.success("One-pager generated.")
    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=f"moog_investor_snapshot_{dt.date.today().isoformat()}.pdf",
        mime="application/pdf",
        type="primary",
    )
else:
    st.info("Click **Generate One-Pager** to pull fresh data and build the PDF.")
