"""
Moog brand styling, sampled directly from moog.com/investors.html:
  - Primary color: deep maroon/burgundy #87212E (nav bar, buttons, accent text)
  - Heading text: near-black #25292B, Open Sans Light (weight 300)
  - Body text: Open Sans Regular
  - Font stack: "Open Sans", "Helvetica Neue", Arial, sans-serif

inject_moog_theme() should be called once near the top of every page, right
after st.set_page_config().
"""

import textwrap

import streamlit as st

MAROON = "#87212E"
MAROON_DARK = "#5E1620"
MAROON_LIGHT = "#F3E4E6"
INK = "#25292B"
GRAY = "#5C6368"
GRAY_LIGHT = "#F2F2F2"
WHITE = "#FFFFFF"

FONT_STACK = '"Open Sans", "Helvetica Neue", Helvetica, Arial, sans-serif'

# Categorical palette for multi-series charts. Moog maroon always leads so
# Moog's own series reads consistently across every chart in the app.
CHART_COLORS = [
    MAROON,      # Moog
    "#2E4057",   # slate navy
    "#1B7F79",   # teal
    "#C98A2B",   # gold
    "#5C6BC0",   # indigo
    "#4C7A4C",   # green
    "#8C6A4E",   # brown
    "#6C6C6C",   # neutral gray
]


def inject_moog_theme() -> None:
    # NOTE: this CSS must be fully dedented (no leading whitespace on any
    # line) before reaching st.markdown. CommonMark treats 4+ leading spaces
    # as an indented code block, which — depending on the exact markdown-it
    # version Streamlit resolves — can cause the raw CSS text to be printed
    # on the page instead of applied as a <style> tag, even with
    # unsafe_allow_html=True. textwrap.dedent() strips the common Python
    # source indentation so this can't happen regardless of parser version.
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');

    html, body, [class*="css"] {{
        font-family: {FONT_STACK};
        color: {INK};
    }}

    /* Headings: light weight, tight tracking — matches moog.com */
    h1, h2, h3 {{
        font-family: {FONT_STACK};
        font-weight: 300 !important;
        color: {INK} !important;
        letter-spacing: -0.01em;
    }}
    h1 {{ border-bottom: 3px solid {MAROON}; padding-bottom: 0.4rem; }}
    h4, h5, h6 {{ font-weight: 600 !important; color: {INK} !important; }}

    /* Maroon accents on interactive elements */
    a, a:visited {{ color: {MAROON}; }}
    a:hover {{ color: {MAROON_DARK}; }}

    div[data-testid="stMetricValue"] {{
        color: {INK};
        font-weight: 600;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {GRAY};
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.78rem;
        letter-spacing: 0.02em;
    }}
    div[data-testid="stMetricDelta"] svg {{ display: inline; }}

    /* Buttons / link-buttons */
    .stButton > button, .stLinkButton > a, div[data-testid="stLinkButton"] a {{
        background-color: {MAROON} !important;
        color: {WHITE} !important;
        border: 1px solid {MAROON} !important;
        border-radius: 2px !important;
        font-weight: 600 !important;
    }}
    .stButton > button:hover, .stLinkButton > a:hover {{
        background-color: {MAROON_DARK} !important;
        border-color: {MAROON_DARK} !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {GRAY_LIGHT};
        border-right: 1px solid #E3E3E3;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {MAROON} !important;
        font-weight: 600 !important;
    }}

    /* Tabs */
    button[data-baseweb="tab"] {{ font-weight: 600; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {MAROON} !important; }}
    div[data-baseweb="tab-highlight"] {{ background-color: {MAROON} !important; }}

    /* Dataframes / tables header accent */
    thead tr th {{ color: {INK}; }}

    /* Divider color */
    hr {{ border-top: 1px solid #E3E3E3; }}

    /* Caption / small text */
    [data-testid="stCaptionContainer"], .stCaption {{ color: {GRAY}; }}
    </style>
    """
    st.markdown(textwrap.dedent(css).strip(), unsafe_allow_html=True)
