"""
Stage 3: Leaf Builder Construction.
"""
from __future__ import annotations

from typing import Any

from betydb_extraction.normalizer.builders.base import ClassifiedBlock, Disposition
from betydb_extraction.normalizer.builders.caption import CaptionBuilder
from betydb_extraction.normalizer.builders.equation import EquationBuilder
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.footnote import FootnoteBuilder
from betydb_extraction.normalizer.builders.page_footer import PageFooterBuilder
from betydb_extraction.normalizer.builders.page_header import PageHeaderBuilder
from betydb_extraction.normalizer.builders.paragraph import ParagraphBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.reference import ReferenceBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder

# Union type alias for all builders Stage 3 can produce.
# (Section builders are excluded — they are produced by Stage 7.)
ObjectBuilder = (
    ParagraphBuilder
    | EquationBuilder
    | FootnoteBuilder
    | ReferenceBuilder
    | PageHeaderBuilder
    | PageFooterBuilder
    | TableBuilder
    | FigureBuilder
)

# ── kind literal constants ────────────────────────────────────────────────────
# These are the Schema v1.1 discriminated-union literal values for each type.
# Read once from the schema; not computed at runtime.
_KIND_PARAGRAPH   = "paragraph"
_KIND_EQUATION    = "equation"
_KIND_FOOTNOTE    = "footnote"
_KIND_REFERENCE   = "reference"
_KIND_PAGE_HEADER = "page_header"
_KIND_PAGE_FOOTER = "page_footer"
_KIND_TABLE       = "table"
_KIND_FIGURE      = "figure"

# Dispositions that produce NO builder in Stage 3:
_NO_BUILDER_DISPOSITIONS: frozenset[Disposition] = frozenset({
    Disposition.CAPTION_TEXT,
    Disposition.TABLE_CELL_EVIDENCE,
    Disposition.GENUINE_SECTION_HEADER,
    Disposition.CAPTION_LABEL,
    Disposition.PICTURE,
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _html(block: Any) -> str:
    """Return block.html, defaulting to empty string if absent or None."""
    return getattr(block, "html", "") or ""


def _make_provenance(block: Any, page_number: int) -> ProvenanceBuilder:
    return ProvenanceBuilder(
        marker_block_ids=[block.id],
        page_number=page_number,
        bbox=getattr(block, "bbox", None),
        polygon=getattr(block, "polygon", None),
        # contributing_bboxes: not set at Stage 3 (only Pattern-B captions use it)
        contributing_bboxes=None,
        # reading_order_index: Stage 8
        reading_order_index=None,
        # section_path: Stage 7
        section_path=[],
    )


def _image_data(block: Any) -> bytes | None:
    images: dict | None = getattr(block, "images", None)
    if not images:
        return None
    for value in images.values():
        if value:
            if isinstance(value, bytes):
                return value
            if isinstance(value, str):
                import base64
                try:
                    return base64.b64decode(value)
                except Exception:
                    return value.encode()
    return None


# ── Builder constructors ──────────────────────────────────────────────────────

def _build_paragraph(block: Any, page_number: int) -> ParagraphBuilder:
    return ParagraphBuilder(
        kind=_KIND_PARAGRAPH,
        text=_html(block),
        provenance=_make_provenance(block, page_number),
        # deferred
        canonical_path=None,
        
    )


def _build_equation(block: Any, page_number: int) -> EquationBuilder:
    return EquationBuilder(
        kind=_KIND_EQUATION,
        raw_math=_html(block),
        equation_number=None,           # deferred-population slot
        provenance=_make_provenance(block, page_number),
        canonical_path=None,
     
    )


def _build_footnote(block: Any, page_number: int) -> FootnoteBuilder:
    return FootnoteBuilder(
        kind=_KIND_FOOTNOTE,
        raw_text=_html(block),
        attached_object_id=None,        # Stage 6
        provenance=_make_provenance(block, page_number),
        canonical_path=None,
 
    )


def _build_reference(block: Any, page_number: int) -> ReferenceBuilder:
    return ReferenceBuilder(
        kind=_KIND_REFERENCE,
        raw_text=_html(block),
        provenance=_make_provenance(block, page_number),
        canonical_path=None,
  
    )


def _build_page_header(block: Any, page_number: int) -> PageHeaderBuilder:
    return PageHeaderBuilder(
        kind=_KIND_PAGE_HEADER,
        raw_text=_html(block),
        provenance=_make_provenance(block, page_number),
        canonical_path=None,
    
    )


def _build_page_footer(block: Any, page_number: int) -> PageFooterBuilder:
    return PageFooterBuilder(
        kind=_KIND_PAGE_FOOTER,
        raw_text=_html(block),
        provenance=_make_provenance(block, page_number),
        canonical_path=None,
   
    )


def _build_table(block: Any, page_number: int) -> TableBuilder:
    return TableBuilder(
        kind=_KIND_TABLE,
        raw_html=_html(block),
        caption=None,           # Stage 4
        rows=[],                # Stage 5
        cells=[],               # Stage 5 (bare tables keep [])
        footnote_ids=[],        # Stage 6
        provenance=_make_provenance(block, page_number),
        canonical_path=None,
 
    )


def _build_figure(block: Any, page_number: int) -> FigureBuilder:
    return FigureBuilder(
        kind=_KIND_FIGURE,
        image_data=_image_data(block),
        caption=None,           # Stage 4
        footnote_ids=[],        # Stage 6
        provenance=_make_provenance(block, page_number),
        canonical_path=None,
    
    )


# ── Dispatch table ────────────────────────────────────────────────────────────

_BUILDER_DISPATCH: dict[Disposition, Any] = {
    Disposition.BODY_PARAGRAPH:  _build_paragraph,
    Disposition.EQUATION:        _build_equation,
    Disposition.FOOTNOTE:        _build_footnote,
    Disposition.REFERENCE_ENTRY: _build_reference,
    Disposition.PAGE_HEADER:     _build_page_header,
    Disposition.PAGE_FOOTER:     _build_page_footer,
    Disposition.TABLE_SHELL:     _build_table,
    Disposition.FIGURE_SHELL:    _build_figure,
}


# ── Public entry point ────────────────────────────────────────────────────────

def build_leaf_builders(
    classified_seq: list[ClassifiedBlock],
    page_number: int,
) -> list[ObjectBuilder]:
    builders: list[ObjectBuilder] = []

    for cb in classified_seq:
        disposition = cb.disposition

        if disposition in _NO_BUILDER_DISPOSITIONS:
            # Intentionally skipped — consumed by Stages 4, 5, or 7, or
            # discarded (PICTURE, already logged in Stage 2).
            continue

        constructor = _BUILDER_DISPATCH.get(disposition)
        if constructor is None:
            # Should never happen if Stage 2's classification table is
            # complete — but fail loudly rather than silently dropping.
            raise RuntimeError(
                f"Stage 3: no builder constructor for disposition "
                f"{disposition!r} (block id={cb.unwrapped.block.id!r}, "
                f"page_index={page_number})"
            )

        builder = constructor(cb.unwrapped.block, page_number)
        builders.append(builder)

    return builders