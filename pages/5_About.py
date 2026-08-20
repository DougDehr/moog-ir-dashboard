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
| Company narrative (segments, "Why Invest" pillars, IR site structure) | [moog.com/investors](https://www.moog.com/investors.html) | Summarized, not reproduced verbatim. |

### Peer / competitor set

""" + "\n".join(f"- **{t}** — {name}" for t, name in config.PEERS.items()) + """

This set was chosen as the aerospace & defense / precision-motion-control companies most commonly used as
Moog's public-market comparables: flight-control actuation, motion control, and aerospace component
suppliers of broadly comparable or adjacent scale. It is not an official Moog-designated peer group.

### Refresh cadence

Price quotes cache for ~15–30 minutes; fundamentals and SEC XBRL data cache for several hours, to stay
well within the fair-access limits of free public APIs.

### Limitations

- Yahoo Finance fundamentals are vendor-normalized and can occasionally be stale, missing, or defined
  slightly differently than GAAP as-filed figures.
- Backlog, segment-level revenue mix, and guidance are reported by Moog in its earnings releases and
  presentation decks but are not standardized XBRL tags, so they are **not** pulled into this dashboard —
  see the official [Financial Materials page](""" + config.IR_LINKS["Financials"] + """) for those figures.
- Moog's fiscal year ends in early October; fiscal quarter labels here follow Moog's own fiscal calendar,
  not the calendar year.

### Disclaimer
""")

st.warning(config.DISCLAIMER)
