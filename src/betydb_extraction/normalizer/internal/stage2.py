"""
Stage 2: Block Classification.
"""
from __future__ import annotations

import re
from typing import Any

from betydb_extraction.normalizer.builders.base import ClassifiedBlock, Disposition, UnwrappedBlock
from betydb_extraction.normalizer.errors import UnrecognizedBlockTypeError
from betydb_extraction.normalizer.logging_util import log_picture_discarded

# ── Constants ─────────────────────────────────────────────────────────────────

# Regex for CAPTION_LABEL override condition (a):
#   Matches "Table 3", "Figure 12.", "TABLE 1:" etc.
_CAPTION_LABEL_RE = re.compile(
    r"^(Table|Figure)\s+\d+[\.:]?\s*$",
    re.IGNORECASE,
)

# block_types that trigger the CAPTION_LABEL lookahead condition (b):
_CAPTION_TARGET_BLOCK_TYPES: frozenset[str] = frozenset({"Table", "Figure"})

# How many subsequent blocks to scan for a Table/Figure in condition (b):
_CAPTION_LOOKAHEAD_WINDOW = 3

# block_types that are wrapper types — must have been consumed by Stage 1.5.
# If one appears here, it was inside another wrapper (inner-wrapper case) and
# is classified normally; its block_type will not be in _DISPATCH, so
# UnrecognizedBlockTypeError fires — intentionally loud per spec §4.2.
_WRAPPER_BLOCK_TYPES: frozenset[str] = frozenset(
    {"TableGroup", "FigureGroup", "ListGroup"}
)

# References section heading vocabulary (spec §5 Stage 2, ListItem rule):
_REFERENCES_VOCABULARY: frozenset[str] = frozenset(
    {"references", "bibliography", "works cited", "literature cited"}
)

# Static dispatch table: block_type → default Disposition.
# Does NOT include SectionHeader or ListItem — those have override logic.
_STATIC_DISPATCH: dict[str, Disposition] = {
    "Text":       Disposition.BODY_PARAGRAPH,
    "Table":      Disposition.TABLE_SHELL,
    "Figure":     Disposition.FIGURE_SHELL,
    "Caption":    Disposition.CAPTION_TEXT,
    "TableCell":  Disposition.TABLE_CELL_EVIDENCE,
    "Equation":   Disposition.EQUATION,
    "Footnote":   Disposition.FOOTNOTE,
    "PageHeader": Disposition.PAGE_HEADER,
    "PageFooter": Disposition.PAGE_FOOTER,
    "Picture":    Disposition.PICTURE,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _html_text(block: Any) -> str:
    """Return block.html stripped of leading/trailing whitespace."""
    return (getattr(block, "html", "") or "").strip()


def _has_table_or_figure_within(
    unwrapped_seq: list[UnwrappedBlock],
    start_index: int,
    window: int,
) -> bool:
    end = min(start_index + window, len(unwrapped_seq))
    for i in range(start_index, end):
        if unwrapped_seq[i].block.block_type in _CAPTION_TARGET_BLOCK_TYPES:
            return True
    return False


def _resolve_section_header_disposition(
    unwrapped: UnwrappedBlock,
    seq: list[UnwrappedBlock],
    current_index: int,
) -> Disposition:
    text = _html_text(unwrapped.block)

    if _CAPTION_LABEL_RE.match(text):
        next_start = current_index + 1
        if _has_table_or_figure_within(seq, next_start, _CAPTION_LOOKAHEAD_WINDOW):
            return Disposition.CAPTION_LABEL

    return Disposition.GENUINE_SECTION_HEADER


def _resolve_list_item_disposition(
    block: Any,
    heading_registry: dict[str, Any],   # marker_block_id → MarkerBlock
    classified_headings: dict[str, Disposition],  # id → disposition so far
) -> Disposition:
    section_hierarchy: dict[str, str] = getattr(
        block, "section_hierarchy", {}
    ) or {}

    if not section_hierarchy:
        return Disposition.BODY_PARAGRAPH

    # Sort depth keys numerically to find the deepest governing section.
    try:
        sorted_keys = sorted(section_hierarchy.keys(), key=lambda k: int(k))
    except (ValueError, TypeError):
        # Non-numeric keys: fall back to lexicographic sort (conservative).
        sorted_keys = sorted(section_hierarchy.keys())

    if not sorted_keys:
        return Disposition.BODY_PARAGRAPH

    deepest_key = sorted_keys[-1]
    deepest_heading_id: str = section_hierarchy[deepest_key]

    heading_block = heading_registry.get(deepest_heading_id)
    if heading_block is None:
        # Heading not found in prior blocks — no governing section resolved.
        return Disposition.BODY_PARAGRAPH

    heading_text = _html_text(heading_block).lower()
    if heading_text in _REFERENCES_VOCABULARY:
        return Disposition.REFERENCE_ENTRY

    return Disposition.BODY_PARAGRAPH


# ── Public entry point ────────────────────────────────────────────────────────

def classify_blocks(
    unwrapped_seq: list[UnwrappedBlock],
    page_index: int,
    heading_registry: dict[str, Any] | None = None,
) -> list[ClassifiedBlock]:
    result: list[ClassifiedBlock] = []

    if heading_registry is None:
        heading_registry = {}

    for i, unwrapped in enumerate(unwrapped_seq):
        block = unwrapped.block
        block_type: str = block.block_type

        # ── SectionHeader (has override logic) ───────────────────────────────
        if block_type == "SectionHeader":
            disposition = _resolve_section_header_disposition(unwrapped, unwrapped_seq, i)
            if disposition == Disposition.GENUINE_SECTION_HEADER:
                # Register immediately so ListItems later in the pass can find it.
                heading_registry[block.id] = block

        # ── ListItem (has override logic) ─────────────────────────────────────
        elif block_type == "ListItem":
            disposition = _resolve_list_item_disposition(
                block, heading_registry, {}
            )

        # ── Picture (static, but requires a log entry) ────────────────────────
        elif block_type == "Picture":
            disposition = Disposition.PICTURE
            log_picture_discarded(
                marker_block_id=block.id,
                page_index=page_index,
            )

        # ── Static dispatch ───────────────────────────────────────────────────
        elif block_type in _STATIC_DISPATCH:
            disposition = _STATIC_DISPATCH[block_type]

        # ── Unrecognised ──────────────────────────────────────────────────────
        else:
            raise UnrecognizedBlockTypeError(
                block_type=block_type,
                marker_block_id=block.id,
                page_index=page_index,
            )

        result.append(ClassifiedBlock(unwrapped=unwrapped, disposition=disposition))

    return result