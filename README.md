# Moog Inc. — Investor Relations Dashboard

An independent, unofficial Streamlit dashboard covering **Moog Inc. (NYSE: MOG.A / MOG.B)**
from an investor-relations angle: stock performance vs. competitors, valuation/margin
comparison, financial trends, and live SEC filings. All data is pulled at runtime from
public sources — nothing is hardcoded or scraped from Moog's site content.

Not affiliated with, endorsed by, or reviewed by Moog Inc. The Moog wordmark in
`assets/moog_logo_maroon.png` is Moog Inc.'s trademark, used here only to identify the
company the dashboard covers.

## Pages

- **Overview** (`app.py`) — Moog logo, live quote strip for both share classes,
  latest-quarter KPIs pulled from SEC XBRL, Moog's "Why Invest" pillars and reportable
  segments, quick links to Moog's official IR site.
- **Stock Performance** — indexed price chart vs. selected competitors and benchmarks
  (S&P 500, Aerospace & Defense ETF), trailing returns table, volatility, beta, dividends.
- **Competitor Analysis** — valuation/margin comparison table, margin bar charts,
  growth-vs-margin bubble chart, Moog-vs-peer-average radar.
- **Analysts** — sell-side price targets and consensus rating for Moog, price-target
  range chart, recommendation trend, recent rating actions, and the same coverage
  metrics compared across competitors (upside/downside to target, # of analysts).
- **Financials** — quarterly revenue/operating income/EPS trend and balance sheet
  snapshot from SEC EDGAR XBRL, with optional peer overlay.
- **Filings & Events** — live recent SEC filings list, plus links to Moog's official
  earnings releases, presentations, and 10-Q/10-K filings.
- **About** — data sources, peer-set rationale, and limitations.

## Data sources

- **Yahoo Finance** (via `yfinance`) — prices, dividends, valuation multiples, margins.
- **SEC EDGAR** (`data.sec.gov` XBRL + submissions APIs) — revenue, net income, EPS,
  balance sheet, filing list. No API key required, but SEC does require a descriptive
  `User-Agent` with a contact string on every request (see Configuration below).

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

Copy the example secrets file and set your own contact email (used only in the SEC
`User-Agent` header, per SEC's fair-access policy — not sent anywhere else):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

`.streamlit/secrets.toml` is git-ignored, so it's safe to put a real email there even if
this repo is public.

## Deploying to Streamlit Community Cloud

1. Push this project to a **public** GitHub repository (Streamlit Community Cloud's free
   tier requires a public repo, or a private one on a paid plan).
   ```bash
   git init
   git add .
   git commit -m "Moog IR dashboard"
   git branch -M main
   git remote add origin <your-repo-url>
   git push -u origin main
   ```
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and click
   **New app**.
3. Select this repo/branch and set the main file path to `app.py`.
4. Under **Advanced settings → Secrets**, paste:
   ```toml
   SEC_CONTACT_EMAIL = "you@example.com"
   ```
5. Deploy. Streamlit Cloud installs `requirements.txt` automatically.

## Notes & limitations

- Twelve-month backlog, segment-level revenue mix, and forward guidance are reported by
  Moog in its earnings release/presentation but aren't standardized XBRL tags, so they
  aren't pulled here — see Moog's official
  [Financial Materials page](https://www.moog.com/investors/financials.html).
- Moog's fiscal year ends in early October; fiscal quarter labels follow Moog's own
  fiscal calendar, not the calendar year.
- Yahoo Finance fundamentals are vendor-normalized and can lag or differ slightly from
  as-filed GAAP figures; SEC XBRL data is closer to source but tag usage can vary by
  company/year, so peer coverage in the Financials page may be incomplete for some tickers.
