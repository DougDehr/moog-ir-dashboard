"""About, methodology, and data source notes."""

import streamlit as st

from src import config
from src.theme import inject_moog_theme

st.set_page_config(page_title="About — Moog IR Dashboard", page_icon="ℹ️", layout="wide")
inject_moog_theme()
st.title("About This Dashboard")

st.markdown("""
This is an independent, unofficial investor-relations style dashboard for **Moog Inc. (NYSE: MOG.A / MOG.B)**,
built entirely from public data. It is **not** produced, reviewed, sponsored, or endorsed by Moog Inc.

### Data sources

| Data | Source | Notes |
|---|---|---|
| Stock prices, dividends, valuation multiples, margins | [Yahoo Finance](https://finance.yahoo.com) via the `yfinance` library | Vendor-calculated fundamentals (P/E, margins, growth) can lag official filings and occasionally differ from as-reported GAAP figures. |
| Revenue, net income, EPS, balance sheet | [SEC EDGAR XBRL](https://www.sec.gov/edgar) `companyconcept` API | Structured data extracted directly from Moog's and peers' XBRL-tagged 10-K/10-Q filings — the same data underlying the filings themselves. |
| Filing list | SEC EDGAR `submissions` API | Live list of recent 10-K/10-Q/8-K filings. |
| Analyst price targets, ratings, estimate revisions, earnings history | [Yahoo Finance](https://finance.yahoo.com) via `yfinance` | Vendor-aggregated from sell-side estimates; can lag individual firms' own publications. |
| Institutional holders, insider (Form 4) transactions | [Yahoo Finance](https://finance.yahoo.com) via `yfinance` | Aggregated from 13F and Form 3/4/5 filings; typically lags the actual filing by several weeks. |
| Short interest, trading volume | [Yahoo Finance](https://finance.yahoo.com) via `yfinance` | Short interest is exchange-reported roughly twice monthly, so it can lag by up to ~2 weeks. |
| Company narrative (segments, "Why Invest" pillars, IR site structure) | [moog.com/investors](https://www.moog.com/investors.html) | Summarized, not reproduced verbatim. |

### Peer / competitor set

""" + "\n".join(f"- **{t}** — {name}" for t, name in config.PEERS.items()) + """

This set was chosen as the aerospace & defense / precision-motion-control companies most commonly used as
Moog's public-market comparables: flight-control actuation, motion control, and aerospace component
suppliers of broadly comparable or adjacent scale. It is not an official Moog-designated peer group.

### Refresh cadence

Price quotes cache for ~20 minutes; price history for ~45 minutes; analyst/ownership/fundamentals data
and SEC XBRL data cache for up to 12 hours — both to stay well within free public APIs' fair-access
limits and to reduce how often this app has to ask Yahoo Finance for the same data twice.

### Limitations

- Yahoo Finance fundamentals are vendor-normalized and can occasionally be stale, missing, or defined
  slightly differently than GAAP as-filed figures.
- Backlog, segment-level revenue mix, and guidance are reported by Moog in its earnings releases and
  presentation decks but are not standardized XBRL tags, so they are **not** pulled into this dashboard —
  see the official [Financial Materials page](""" + config.IR_LINKS["Financials"] + """) for those figures.
- Moog's fiscal year ends in early October; fiscal quarter labels here follow Moog's own fiscal calendar,
  not the calendar year.
- Yahoo Finance periodically rate-limits or blocks requests from shared cloud hosting IP ranges (which
  Streamlit Community Cloud uses) — an ongoing, publicly-documented issue on Yahoo's side, independent of
  this app's own request volume. If a page shows a message that data "couldn't be loaded" from an external
  provider, that's this — it's clearly labeled as the provider's issue, not a bug here, and reloading in a
  few minutes typically resolves it.

### Disclaimer
""")

st.warning(config.DISCLAIMER)
