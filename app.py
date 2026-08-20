"""
Entry point / router.

Streamlit Community Cloud has this file pinned as the app's "main file path"
and that setting can't be changed after deployment. To control the sidebar
label of the first page (without it being forced to match a filename, e.g.
"app"), we use st.navigation() to explicitly declare every page and its
display title, rather than relying on Streamlit's automatic pages/-directory
discovery. Each page's own st.set_page_config() call (in its own file)
still controls that page's browser-tab title/icon.
"""

import streamlit as st

pg = st.navigation([
    st.Page("Summary.py", title="Summary", default=True),
    st.Page("pages/1_Stock_Performance.py", title="Stock Performance"),
    st.Page("pages/2_Competitor_Analysis.py", title="Competitor Analysis"),
    st.Page("pages/3_Analysts.py", title="Analysts"),
    st.Page("pages/4_Financials.py", title="Financials"),
    st.Page("pages/5_Filings_and_Events.py", title="Filings and Events"),
    st.Page("pages/6_About.py", title="About"),
])
pg.run()
