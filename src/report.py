"""One-page PDF snapshot builder for the Export page.

Pure layout — every value it draws is passed in already-fetched, so this
module has no network dependency and can't itself fail on a rate limit.
Uses fpdf2's core Helvetica font (no bundled font file needed) with Moog's
maroon as the accent color.
"""

from __future__ import annotations

from fpdf import FPDF, FontFace

MAROON = (135, 33, 46)
INK = (37, 41, 43)
GRAY = (92, 99, 104)
LIGHT_GRAY = (230, 230, 230)
MAROON_LIGHT = (243, 228, 230)

# fpdf2's core Helvetica font is Latin-1 only (no embedded Unicode font here,
# to avoid bundling a font file) — the app's UI text uses em/en dashes,
# middots, and arrows freely, so every string must be sanitized before it
# reaches pdf.cell()/multi_cell() or fpdf raises FPDFUnicodeEncodingException.
_UNICODE_REPLACEMENTS = {
    "—": "-", "–": "-", "‒": "-",   # em/en/figure dash
    "·": "-", "•": "-",                    # middot, bullet
    "→": "->", "↗": "",                    # right arrow, up-right arrow
    "‘": "'", "’": "'",                    # curly single quotes
    "“": '"', "”": '"',                    # curly double quotes
    "…": "...",                                  # ellipsis
}


def _ascii(value) -> str:
    s = str(value)
    for unicode_char, ascii_equiv in _UNICODE_REPLACEMENTS.items():
        s = s.replace(unicode_char, ascii_equiv)
    return s.encode("latin-1", "replace").decode("latin-1")


class _OnePager(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRAY)
        self.cell(
            0, 10,
            _ascii(
                "Independent, unofficial summary built from public data (Yahoo Finance, SEC EDGAR). "
                "Not affiliated with or endorsed by Moog Inc. Not investment advice."
            ),
            align="C",
        )


def _kpi_box(pdf: _OnePager, x, y, w, h, label, value, value_color=INK, value_size=13):
    pdf.set_xy(x, y)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.rect(x, y, w, h)
    pdf.set_xy(x + 2, y + 2)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*GRAY)
    pdf.cell(w - 4, 4, _ascii(label).upper())
    pdf.set_xy(x + 2, y + h - 10)
    pdf.set_font("Helvetica", "B", value_size)
    pdf.set_text_color(*value_color)
    pdf.cell(w - 4, 8, _ascii(value))


def build_one_pager(
    generated_at: str,
    share_classes: list[dict],          # [{"label": "Class A — MOG.A", "price": "$..", "change": "+.."}, ...]
    market_cap: str,
    week_range: str,
    quarter_label: str,
    net_sales: str,
    net_sales_yoy: str,
    op_margin: str,
    net_income: str,
    net_income_yoy: str,
    diluted_eps: str,
    analyst: dict,                       # {"current": .., "mean_target": .., "upside": .., "num_analysts": .., "consensus": ..}
    ownership: dict,                     # {"institutional": .., "insider": ..}
    short_interest: dict,                # {"short_pct_float": .., "days_to_cover": ..}
    peer_rows: list[list[str]],          # rows for the peer comparison table (already formatted strings)
    peer_headers: list[str],
) -> bytes:
    pdf = _OnePager(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(12, 12, 12)

    # --- Header -------------------------------------------------------
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*MAROON)
    pdf.cell(0, 10, "MOOG INC.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "Investor Snapshot", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, _ascii(f"Generated {generated_at} · NYSE: MOG.A / MOG.B · East Aurora, NY"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_draw_color(*MAROON)
    pdf.set_line_width(0.6)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(4)

    # --- Market snapshot row -------------------------------------------
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "Market Snapshot", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    y0 = pdf.get_y()
    n_boxes = len(share_classes) + 2
    box_w = (196 - 12 - (n_boxes - 1) * 2) / n_boxes
    x = 12
    for sc in share_classes:
        _kpi_box(pdf, x, y0, box_w, 18, sc["label"], sc["price"])
        x += box_w + 2
    _kpi_box(pdf, x, y0, box_w, 18, "Market Cap", market_cap)
    x += box_w + 2
    _kpi_box(pdf, x, y0, box_w, 18, "52-Wk Range", week_range)
    pdf.set_y(y0 + 18 + 4)

    # --- Latest quarter row --------------------------------------------
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, _ascii(f"Latest Reported Quarter — {quarter_label}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    y1 = pdf.get_y()
    labels = [
        ("Net Sales", net_sales, net_sales_yoy),
        ("Operating Margin", op_margin, ""),
        ("Net Income", net_income, net_income_yoy),
        ("Diluted EPS", diluted_eps, ""),
    ]
    box_w2 = (196 - 12 - 3 * 2) / 4
    x = 12
    for label, val, sub in labels:
        _kpi_box(pdf, x, y1, box_w2, 18, label, val)
        if sub:
            pdf.set_xy(x + 2, y1 + 13)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(60, 120, 70)
            pdf.cell(box_w2 - 4, 4, _ascii(sub))
        x += box_w2 + 2
    pdf.set_y(y1 + 18 + 4)

    # --- Analyst + Ownership + Short interest row ------------------------
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "Analyst Coverage, Ownership & Short Interest", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    y2 = pdf.get_y()
    row2 = [
        ("Mean Target", analyst.get("mean_target", "n/a")),
        ("Upside", analyst.get("upside", "n/a")),
        ("# Analysts", analyst.get("num_analysts", "n/a")),
        ("Consensus", analyst.get("consensus", "n/a")),
        ("Inst. Own.", ownership.get("institutional", "n/a")),
        ("Insider Own.", ownership.get("insider", "n/a")),
        ("Short % Float", short_interest.get("short_pct_float", "n/a")),
        ("Days to Cover", short_interest.get("days_to_cover", "n/a")),
    ]
    box_w3 = (196 - 12 - 7 * 2) / 8
    x = 12
    for label, val in row2:
        _kpi_box(pdf, x, y2, box_w3, 16, label, val, value_size=9.5)
        x += box_w3 + 2
    pdf.set_y(y2 + 16 + 6)

    # --- Peer comparison table -------------------------------------------
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Peer Comparison", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("Helvetica", "B", 7.5)
    with pdf.table(
        col_widths=(44, 16, 14, 18, 16, 16, 16, 16),
        text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"),
        line_height=5.2,
        headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=MAROON),
        cell_fill_color=(248, 244, 244),
        cell_fill_mode="ROWS",
        borders_layout="HORIZONTAL_LINES",
    ) as table:
        header_row = table.row()
        for h in peer_headers:
            header_row.cell(_ascii(h))
        pdf.set_font("Helvetica", "", 7.5)
        for r in peer_rows:
            row = table.row()
            for cell_val in r:
                row.cell(_ascii(cell_val))

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(
        0, 4,
        "Sources: Yahoo Finance (prices, valuation, analyst, ownership, short interest data) and SEC EDGAR "
        "XBRL (net sales, operating margin, net income, diluted EPS). Figures are as of the data pulled at "
        "generation time and may lag official filings/publications.",
    )

    out = pdf.output()
    return bytes(out)
