"""Recent SEC filings (live from EDGAR) plus links to Moog's official IR materials."""

import streamlit as st

from src import config
from src.data_sources import get_recent_filings
from src.theme import inject_moog_theme

st.set_page_config(page_title="Filings & Events — Moog IR Dashboard", page_icon="📰", layout="wide")
inject_moog_theme()
st.title("📰 Filings & Events")

st.subheader("Recent SEC Filings")
st.caption("Live from SEC EDGAR's submissions API (data.sec.gov) for Moog Inc. (CIK 0000067887).")

forms = st.multiselect("Filing types", options=["10-K", "10-Q", "8-K", "DEF 14A", "4", "3"],
                        default=["10-K", "10-Q", "8-K"])

with st.spinner("Fetching filing history from SEC EDGAR…"):
    filings = get_recent_filings(config.COMPANY_CIK, forms=tuple(forms), limit=20)

if filings.empty:
    st.warning("No filings returned — SEC EDGAR may be temporarily unavailable.")
else:
    for _, row in filings.iterrows():
        desc = row["primaryDocDescription"] or row["form"]
        st.markdown(f"**{row['filingDate']}** — `{row['form']}` — {desc}  \n[View on SEC EDGAR ↗]({row['url']})")
        st.divider()

st.subheader("Official Moog Investor Materials")
st.caption("Earnings press releases, conference calls, and quarterly presentation decks are hosted directly by Moog — link out below.")
for label, url in config.IR_LINKS.items():
    st.markdown(f"- [{label}]({url})")

st.info(
    f"{config.FISCAL_YEAR_END_NOTE} Quarterly labels (Q1–Q4) refer to Moog's fiscal quarters, "
    "not calendar quarters."
)
