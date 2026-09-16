"""
assets/generate_mock_pdf.py
"""

from __future__ import annotations
import textwrap
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

PAGE_W, PAGE_H = LETTER  # 612 x 792 pt
MARGIN_L = 72
MARGIN_R = 72
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R
LINE_LEADING = 14
BLOCK_GAP = 18
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

OUT_PATH = "assets/mock_paper.pdf"

# (anchor, text, font, font_size, chars_per_line) grouped by page.
PAGES = [
    [  # Page 1
        ("b:0006",
         "Canopy Architecture and Morphology of Switchgrass Populations "
         "Differing in Forage Yield", FONT_BOLD, 14, 60),
        ("b:0007",
         "Daren D. Redfearn, Kenneth J. Moore, Kenneth P. Vogel, "
         "Steven S. Waller, and Robert B. Mitchell", FONT, 11, 80),
        ("b:0008",
         "Department of Agronomy, University of Nebraska, Lincoln, NE 68583",
         FONT, 10, 90),
        ("b:0009",
         "ABSTRACT\nCanopy architecture influences forage accumulation and "
         "light interception in switchgrass (Panicum virgatum L.). Two "
         "switchgrass populations selected for divergent forage yield were "
         "evaluated for canopy structure over two growing seasons.",
         FONT, 10, 92),
        ("b:0010",
         "Published in Agron. J. 89:262-269 (1997).", FONT, 9, 90),
    ],
    [  # Page 2
        ("b:0011",
         "MATERIALS AND METHODS\nField studies were conducted at the "
         "University of Nebraska Agricultural Research and Development "
         "Center near Mead, NE, on a Sharpsburg silty clay loam soil.",
         FONT, 10, 92),
        ("b:0012",
         "Two switchgrass populations, a high-yielding cycle-2 (HY C2) "
         "population and the unselected cultivar 'Trailblazer', were "
         "established in 1993 in a randomized complete block design with "
         "four replications.", FONT, 10, 92),
        ("b:0013",
         "Plots were harvested at three stages of maturity: vegetative, "
         "elongation, and anthesis, in each of the two years of the study "
         "(1994 and 1995).", FONT, 10, 92),
        ("b:0014",
         "Nitrogen fertilizer was applied each spring at a rate of 112 kg "
         "N ha-1 as ammonium nitrate.", FONT, 10, 92),
    ],
    [  # Page 3
        ("b:0015",
         "RESULTS AND DISCUSSION\nLeaf area index (LAI) differed "
         "significantly (P < 0.05) between populations at the elongation "
         "stage, with HY C2 averaging 3.8 and Trailblazer averaging 3.1.",
         FONT, 10, 92),
        ("b:0016",
         "Canopy height at anthesis averaged 142 cm for HY C2 and 128 cm "
         "for Trailblazer across both years.", FONT, 10, 92),
        ("b:0017",
         "Light interception exceeded 90% for both populations once "
         "canopy height reached approximately 60 cm.", FONT, 10, 92),
    ],
]


def wrap_lines(text: str, chars_per_line: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=chars_per_line) or [""])
    return lines


def main():
    c = canvas.Canvas(OUT_PATH, pagesize=LETTER)
    provenance = []  # list of dicts: anchor, page (1-indexed), polygon (normalized, top-left origin)

    for page_index, blocks in enumerate(PAGES):
        page_num = page_index + 1
        cursor_y_top = 60  # distance from top of page, grows downward

        c.setFont(FONT, 8)
        c.setFillGray(0.55)
        c.drawString(MARGIN_L, PAGE_H - 36, f"Agron. J. 89:262-269 (1997)  —  page {page_num}")
        c.setFillGray(0)

        for anchor, text, font, size, chars_per_line in blocks:
            lines = wrap_lines(text, chars_per_line)
            block_h = len(lines) * LINE_LEADING

            block_top = cursor_y_top
            block_bottom = cursor_y_top + block_h

            c.setFont(font, size)
            for i, line in enumerate(lines):
                baseline_y_top = block_top + (i + 1) * LINE_LEADING - 3
                y_reportlab = PAGE_H - baseline_y_top
                c.drawString(MARGIN_L, y_reportlab, line)

            # Normalized top-left-origin bounding box, with a little padding
            # so the highlight doesn't hug the glyphs too tightly.
            pad = 3
            x0 = (MARGIN_L - pad) / PAGE_W
            x1 = (MARGIN_L + CONTENT_W + pad) / PAGE_W
            y0 = (block_top - pad) / PAGE_H
            y1 = (block_bottom + pad) / PAGE_H

            provenance.append({
                "anchor": anchor,
                "page": page_num,
                "polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
            })

            cursor_y_top = block_bottom + BLOCK_GAP

        c.showPage()

    c.save()
    print(f"Wrote {OUT_PATH}")
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()