"""
Stage 0: Front-Matter Detection.
"""
from __future__ import annotations

import re
from typing import Any

from betydb_extraction.normalizer.logging_util import log_front_matter_detection

# ── Signal patterns ───────────────────────────────────────────────────────────

_S1_STRING = "Submit your article"

_S2_RE = re.compile(r"\bISSN\s*[\d\-]{4,10}")
_S3_RE = re.compile(r"Article views:\s*\d+")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _concatenate_text_blocks(page_block: Any) -> str:
    """
    Return the concatenated plain text of all Text-typed blocks in a page's
    raw children array (one level deep, since S1/S2/S3 are content signals).

    Uses .html as the text source, which matches how all other stages access
    block text content.
    """
    parts: list[str] = []
    for child in page_block.children:
        if child.block_type == "Text":
            parts.append(getattr(child, "html", "") or "")
    return " ".join(parts)


def _has_section_header(page_block: Any) -> bool:
    """
    Return True if any block in the page's raw children array has
    block_type == "SectionHeader".

    Checked before Stage 1.5 unwrapping — operates on the raw children array.
    Wrapper children are NOT inspected (S4 is a one-level check on direct
    page children, per the structural nature of the signal).
    """
    for child in page_block.children:
        if child.block_type == "SectionHeader":
            return True
    return False


# ── Public entry point ────────────────────────────────────────────────────────

def detect_front_matter(page_blocks: list[Any]) -> dict[int, bool]:
    """
    Run front-matter detection on every page and return a flags mapping.

    Parameters
    ----------
    page_blocks:
        marker_document.children — the ordered list of top-level page blocks.

    Returns
    -------
    dict[int, bool]
        page_index (0-based) → is_front_matter.
        Every page index present in the input has an entry in the output.
    """
    flags: dict[int, bool] = {}

    for page_index, page_block in enumerate(page_blocks):
        text = _concatenate_text_blocks(page_block)
        signals_fired: list[str] = []

        # S1 — fixed string, case-sensitive
        if _S1_STRING in text:
            signals_fired.append("S1")

        # S2 — ISSN regex
        if _S2_RE.search(text):
            signals_fired.append("S2")

        # S3 — article views regex
        if _S3_RE.search(text):
            signals_fired.append("S3")

        # S4 — structural: no SectionHeader present on the page
        if not _has_section_header(page_block):
            signals_fired.append("S4")

        # Threshold: at least two signals must fire (S4 alone is not enough,
        # but two signals including S4 are sufficient).
        is_front_matter = len(signals_fired) >= 2

        log_front_matter_detection(
            page_index=page_index,
            signals_fired=signals_fired,
            is_front_matter=is_front_matter,
        )

        flags[page_index] = is_front_matter

    return flags