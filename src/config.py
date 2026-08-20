"""
Static reference data: tickers, CIKs, segments, and site metadata.

Everything financial/price-related is fetched live from public sources at
runtime (Yahoo Finance via yfinance, SEC EDGAR via data.sec.gov). This module
only holds identifiers and descriptive copy, most of it drawn directly from
Moog's own investor relations site (moog.com/investors) so the dashboard's
structure mirrors how Moog presents itself to shareholders.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Company identity
# ---------------------------------------------------------------------------

COMPANY_NAME = "Moog Inc."
COMPANY_CIK = "0000067887"  # SEC EDGAR Central Index Key for Moog Inc.
COMPANY_HQ = "East Aurora, NY"
FISCAL_YEAR_END_NOTE = "Moog's fiscal year ends in early October (not calendar Dec 31)."

# Moog trades as two share classes on the NYSE. Yahoo Finance represents the
# share-class dot as a hyphen (e.g. "MOG.A" -> "MOG-A").
SHARE_CLASSES = {
    "Class A — MOG.A": "MOG-A",
    "Class B — MOG.B": "MOG-B",
}
PRIMARY_TICKER = "MOG-A"  # Class A is the more liquid, commonly-quoted class

IR_LINKS = {
    "Investor Relations Home": "https://www.moog.com/investors.html",
    "News": "https://www.moog.com/investors/news.html",
    "Events and Presentations": "https://www.moog.com/investors/events-presentations.html",
    "Financials": "https://www.moog.com/investors/financials.html",
    "Stock Info": "https://www.moog.com/investors/stock-information.html",
    "Corporate Governance": "https://www.moog.com/investors/corporate-governance.html",
    "Shareholder Services": "https://www.moog.com/investors/shareholder-services.html",
    "Sustainability": "https://www.moog.com/sustainability.html",
}

# "Why Invest in Moog?" — the five pillars Moog itself uses on ir.moog.com,
# summarized here for context (not verbatim reproduction).
WHY_INVEST_PILLARS = [
    ("Market Differentiation",
     "Product innovation and close customer collaboration on demanding technical requirements "
     "across diverse end markets."),
    ("Foundation and Growth",
     "Dominant positions in precision motion control technologies underpin a strong base for "
     "sustained growth."),
    ("Leadership Excellence",
     "Leadership focused on customers, people, community and the planet, aimed at strengthening "
     "financial performance."),
    ("Financial Strength",
     "Effective pricing and simplification initiatives, including 80/20 methodology, support "
     "sustainable financial performance."),
    ("Focused Capital Deployment",
     "Targeted investment in high organic-growth facilities and manufacturing capability to "
     "drive shareholder returns."),
]

# Moog's four reportable segments (confirmed from the FY2026 Q3 Form 10-Q).
SEGMENTS = [
    ("Military Aircraft",
     "Flight controls, actuation and other systems for military fixed-wing and rotary-wing aircraft."),
    ("Commercial Aircraft",
     "Flight control actuation and systems sold to commercial OEMs and the aftermarket."),
    ("Space and Defense",
     "Spacecraft components and satellite buses, launch vehicle and missile controls, naval and "
     "ground defense systems, and turreted weapon systems."),
    ("Industrial",
     "Motion control components and systems for simulation, medical, industrial automation, "
     "energy and other industrial markets."),
]

# ---------------------------------------------------------------------------
# Competitor / peer set
# ---------------------------------------------------------------------------
# Chosen as the aerospace & defense / precision-motion-control names most
# commonly used as Moog's public-market peer group (motion control, flight
# control actuation, and aerostructures/components suppliers of comparable
# or adjacent scale).

PEERS = {
    "WWD": "Woodward, Inc.",
    "PH": "Parker Hannifin Corporation",
    "TDG": "TransDigm Group Incorporated",
    "CW": "Curtiss-Wright Corporation",
    "HEI": "HEICO Corporation",
    "HON": "Honeywell International Inc.",
    "RTX": "RTX Corporation",
}

BENCHMARKS = {
    "S&P 500 (^GSPC)": "^GSPC",
    "Aerospace & Defense ETF (ITA)": "ITA",
}

ALL_PEER_TICKERS = list(PEERS.keys())

# ---------------------------------------------------------------------------
# SEC EDGAR access
# ---------------------------------------------------------------------------
# SEC requires a descriptive User-Agent with a contact string on every
# request to sec.gov / data.sec.gov. We do NOT embed any individual's
# personal email in source (this app is meant to be pushed to a public repo
# for Streamlit Community Cloud). Deployers can override the contact string
# via .streamlit/secrets.toml -> SEC_CONTACT_EMAIL.


def sec_user_agent() -> str:
    contact = "contact@example.com"
    try:
        contact = st.secrets.get("SEC_CONTACT_EMAIL", contact)
    except Exception:
        pass
    return f"MoogIRDashboard/1.0 ({contact})"


DISCLAIMER = (
    "This dashboard is an independent, unofficial tool built entirely from public data "
    "(Yahoo Finance and SEC EDGAR). It is not produced, reviewed, or endorsed by Moog Inc., "
    "and nothing here is investment advice. Data may be delayed, incomplete, or contain "
    "vendor errors — verify against Moog's official filings and ir page at "
    "https://www.moog.com/investors.html before relying on it."
)
