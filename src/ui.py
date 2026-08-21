"""Shared UI helpers — reusable Streamlit message banners.

Centralized here so every page reports upstream data-provider failures with
the same, clear framing: this is the external provider throttling/blocking
requests, not a bug in this dashboard.
"""

import streamlit as st


def external_data_unavailable(what: str, provider: str = "Yahoo Finance", level: str = "error") -> None:
    """Show a banner for a failed external-data fetch, framed as the provider's issue, not ours.

    what: short description of what couldn't be loaded, e.g. "fundamentals for the selected peers".
    provider: the upstream service, e.g. "Yahoo Finance" or "SEC EDGAR".
    level: "error" (blocks the page/section) or "warning" (page still usable without it).
    """
    extra = " (a known issue: it rate-limits requests from shared cloud hosting)" if provider == "Yahoo Finance" else ""
    msg = (
        f"Couldn't load {what} from {provider} right now. **This is {provider} throttling or rate-limiting "
        f"requests on their end{extra}, not a problem with this dashboard.** It's almost always temporary — "
        f"try again in a few minutes."
    )
    (st.error if level == "error" else st.warning)(msg)
