"""
Stage 10: Materialization.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.section import SectionBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.footnote import FootnoteBuilder
from betydb_extraction.normalizer.context import NormalizerProcessingContext
from betydb_extraction.normalizer.builders.base import Disposition
from betydb_extraction.normalizer.logging_util import log_materialization_complete

# Schema v1.1 frozen models — imported here only (all other stages work with
# builders exclusively).
from betydb_extraction.document.document import Document
from betydb_extraction.document.page import Page
from betydb_extraction.document.section import Section
from betydb_extraction.document.paragraph import Paragraph
from betydb_extraction.document.table import Table, TableRow, TableRowCell, TableCell
from betydb_extraction.document.figure import Figure
from betydb_extraction.document.caption import Caption
from betydb_extraction.document.equation import Equation
from betydb_extraction.document.footnote import Footnote
from betydb_extraction.document.reference import Reference
from betydb_extraction.document.page_furniture import PageHeader, PageFooter
from betydb_extraction.document.provenance import BoundingBox, Polygon, StructuralProvenance
from betydb_extraction.document.metadata import Metadata
from betydb_extraction.document.statistics import Statistics
from betydb_extraction.document.processing_metadata import ProcessingMetadata

logger = logging.getLogger(__name__)

def _convert_bbox(marker_bbox: Any) -> BoundingBox | None:
  
    if marker_bbox is None:
        return None
    return BoundingBox(
        x0=marker_bbox.x0, y0=marker_bbox.y0,
        x1=marker_bbox.x1, y1=marker_bbox.y1,
    )


def _convert_polygon(marker_polygon: Any) -> Polygon | None:
    
    if marker_polygon is None:
        return None
    points = tuple((p.x, p.y) for p in marker_polygon)
    return Polygon(points=points)

def _sha256_prefix(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:length]


def _compute_document_id(source_pdf_identifier: str) -> str:
    return "betydoc:" + _sha256_prefix(source_pdf_identifier)


def _compute_object_id(document_id: str, canonical_path: str) -> str:
    return "doc:" + _sha256_prefix(document_id + "|" + canonical_path)

_REFERENCE_TARGET_TYPES = (SectionBuilder, TableBuilder, FigureBuilder, FootnoteBuilder)


def _own_marker_block_id(builder: Any) -> str | None:
    if isinstance(builder, SectionBuilder):
        return builder.heading_marker_block_id

    mids = getattr(getattr(builder, "provenance", None), "marker_block_ids", None)
    if mids:
        return mids[0]
    return None


def _build_marker_id_to_final_id_map(
    page_builders: list[PageBuilder],
    document_id: str,
) -> dict[str, str]:
    mapping: dict[str, str] = {}

    def _register(builder: Any) -> None:
        if not isinstance(builder, _REFERENCE_TARGET_TYPES):
            return
        canonical_path = getattr(builder, "canonical_path", None)
        if canonical_path is None:
            raise ValueError(
                f"Stage 10: {type(builder).__name__} has no canonical_path — "
                "Stage 9 must run before Stage 10."
            )
        own_id = _own_marker_block_id(builder)
        if own_id is None:
            raise ValueError(
                f"Stage 10: {type(builder).__name__} has no resolvable "
                "Marker block id — cannot register as a translation target."
            )
        mapping[own_id] = _compute_object_id(document_id, canonical_path)

    def _walk(items: list[Any]) -> None:
        for item in items:
            _register(item)
            if isinstance(item, SectionBuilder):
                _walk(item.children)

    for pb in page_builders:
        _walk(pb.children)

    return mapping


def _translate_reference(
    marker_block_id: str,
    id_map: dict[str, str],
    *,
    context: str,
) -> str:
    final_id = id_map.get(marker_block_id)
    if final_id is None:
        raise ValueError(
            f"Stage 10: dangling interim reference in {context} — "
            f"marker_block_id={marker_block_id!r} does not resolve to any "
            "materialized Section/Table/Figure/Footnote in the tree."
        )
    return final_id

def _materialize_provenance(
    prov_builder: Any,
    document_id: str,
    id_map: dict[str, str],
) -> StructuralProvenance:
    contributing = prov_builder.contributing_bboxes
    translated_section_path = [
        _translate_reference(
            heading_marker_id, id_map, context="StructuralProvenance.section_path"
        )
        for heading_marker_id in prov_builder.section_path
    ]
    return StructuralProvenance(
        marker_block_ids=list(prov_builder.marker_block_ids),
        page_number=prov_builder.page_number,
        bbox=_convert_bbox(prov_builder.bbox),
        contributing_bboxes=(
            [_convert_bbox(b) for b in contributing] if contributing else None
        ),
        polygon=_convert_polygon(prov_builder.polygon),
        section_path=translated_section_path,
        reading_order_index=prov_builder.reading_order_index,
    )


def _mat_table_row_cell(b: Any, document_id: str) -> TableRowCell:
    return TableRowCell(
        text=b.text or "",
        is_header=b.is_header,
        structural_notes=b.structural_notes,
    )


def _mat_table_row(b: Any, document_id: str) -> TableRow:
    cells = [_mat_table_row_cell(c, document_id) for c in (b.cells or [])]
    return TableRow(
        cells=cells,
    )


def _mat_table_cell(b: Any, document_id: str) -> TableCell:
    return TableCell(
        id=_compute_object_id(document_id, b.canonical_path),
        text=b.text,
        bbox=_convert_bbox(b.bbox),
        polygon=_convert_polygon(b.polygon),
    )


def _mat_caption(b: Any, document_id: str, id_map: dict[str, str]) -> Caption:
    return Caption(
        label=b.label,
        text=b.text,
        trailing_notes=b.trailing_notes,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_paragraph(b: Any, document_id: str, id_map: dict[str, str]) -> Paragraph:
    return Paragraph(
        kind=b.kind,
        id=_compute_object_id(document_id, b.canonical_path),
        text=b.text,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_equation(b: Any, document_id: str, id_map: dict[str, str]) -> Equation:
    return Equation(
        kind=b.kind,
        id=_compute_object_id(document_id, b.canonical_path),
        raw_math=b.raw_math,
        equation_number=b.equation_number,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_footnote(b: Any, document_id: str, id_map: dict[str, str]) -> Footnote:
    attached_final_id = None
    if b.attached_object_id is not None:
        attached_final_id = _translate_reference(
            b.attached_object_id, id_map, context="Footnote.attached_object_id"
        )

    return Footnote(
        kind=b.kind,
        id=_compute_object_id(document_id, b.canonical_path),
        raw_text=b.raw_text,
        attached_object_id=attached_final_id,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_reference(b: Any, document_id: str, id_map: dict[str, str]) -> Reference:
    return Reference(
        kind=b.kind,
        id=_compute_object_id(document_id, b.canonical_path),
        raw_text=b.raw_text,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_page_header(b: Any, document_id: str, id_map: dict[str, str]) -> PageHeader:
    return PageHeader(
        kind=b.kind,
        id=_compute_object_id(document_id, b.canonical_path),
        raw_text=b.raw_text,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_page_footer(b: Any, document_id: str, id_map: dict[str, str]) -> PageFooter:
    return PageFooter(
        kind=b.kind,
        id=_compute_object_id(document_id, b.canonical_path),
        raw_text=b.raw_text,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_table(b: Any, document_id: str, id_map: dict[str, str]) -> Table:
    rows = [_mat_table_row(r, document_id) for r in (b.rows or [])]
    cells = [_mat_table_cell(c, document_id) for c in (b.cells or [])]
    caption = (
        _mat_caption(b.caption, document_id, id_map) if b.caption is not None else None
    )
    footnote_ids = [
        _translate_reference(fid, id_map, context="Table.footnote_ids")
        for fid in (b.footnote_ids or [])
    ]
    return Table(
        kind=b.kind,
        id=_compute_object_id(document_id, b.canonical_path),
        raw_html=b.raw_html,
        rows=rows,
        cells=cells,
        caption=caption,
        footnote_ids=footnote_ids,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


def _mat_figure(b: Any, document_id: str, id_map: dict[str, str]) -> Figure:
    caption = _mat_caption(b.caption, document_id, id_map) if b.caption is not None else None
    return Figure(
        id=_compute_object_id(document_id, b.canonical_path),
        image_data=b.image_data,
        caption=caption,
        provenance=_materialize_provenance(b.provenance, document_id, id_map),
    )


_LEAF_MATERIALIZERS: dict[str, Any] = {
    "ParagraphBuilder": _mat_paragraph,
    "EquationBuilder": _mat_equation,
    "FootnoteBuilder": _mat_footnote,
    "ReferenceBuilder": _mat_reference,
    "PageHeaderBuilder": _mat_page_header,
    "PageFooterBuilder": _mat_page_footer,
    "TableBuilder": _mat_table,
    "FigureBuilder": _mat_figure,
}


def _materialize_leaf(builder: Any, document_id: str, id_map: dict[str, str]) -> Any:
    name = type(builder).__name__
    fn = _LEAF_MATERIALIZERS.get(name)
    if fn is None:
        raise TypeError(
            f"stage10: no materializer registered for builder type {name!r}"
        )
    return fn(builder, document_id, id_map)


def _mat_section_postorder(
    sb: SectionBuilder, document_id: str, id_map: dict[str, str]
) -> Section:
    """
    Recursively materialize a SectionBuilder post-order (children before
    parent).  Returns the frozen Section model.
    """
    materialized_children: list[Any] = []
    for child in sb.children:
        if isinstance(child, SectionBuilder):
            materialized_children.append(
                _mat_section_postorder(child, document_id, id_map)
            )
        else:
            materialized_children.append(
                _materialize_leaf(child, document_id, id_map)
            )

    return Section(
        kind=sb.kind,
        id=_compute_object_id(document_id, sb.canonical_path),
        heading_text=sb.heading_text,
        depth=sb.depth,
        children=materialized_children,
        provenance=_materialize_provenance(sb.provenance, document_id, id_map),
    )


def _count_objects(pages: list[Page]) -> dict[str, int]:
    """
    Recursive type-counting traversal of the materialized page list.
    Returns a dict of field-name → count matching Statistics field names.
    """
    counts: dict[str, int] = {
        "page_count": len(pages),
        "section_count": 0,
        "paragraph_count": 0,
        "table_count": 0,
        "figure_count": 0,
        "equation_count": 0,
        "footnote_count": 0,
        "unresolved_footnote_count": 0,
        "reference_count": 0,
        "page_header_count": 0,
        "page_footer_count": 0,
    }

    def _walk(items: list[Any]) -> None:
        for item in items:
            t = type(item).__name__
            if t == "Section":
                counts["section_count"] += 1
                _walk(item.children)
            elif t == "Paragraph":
                counts["paragraph_count"] += 1
            elif t == "Table":
                counts["table_count"] += 1
            elif t == "Figure":
                counts["figure_count"] += 1
            elif t == "Equation":
                counts["equation_count"] += 1
            elif t == "Footnote":
                counts["footnote_count"] += 1
                if item.attached_object_id is None:
                    counts["unresolved_footnote_count"] += 1
            elif t == "Reference":
                counts["reference_count"] += 1
            elif t == "PageHeader":
                counts["page_header_count"] += 1
            elif t == "PageFooter":
                counts["page_footer_count"] += 1

    for page in pages:
        _walk(page.children)

    return counts


def _extract_title(
    page_builders: list[PageBuilder],
    classified_pages: list[list[Any]],
) -> str | None:
    """
    Return the html of the first GENUINE_SECTION_HEADER-classified block on
    the first non-front-matter page.  None if no such block exists.
    """
    for page_index, page_builder in enumerate(
        sorted(page_builders, key=lambda pb: pb.page_number or 0)
    ):
        if page_builder.is_front_matter:
            continue
        if page_index >= len(classified_pages):
            continue
        for cb in classified_pages[page_index]:
            if cb.disposition == Disposition.GENUINE_SECTION_HEADER:
                return getattr(cb.unwrapped.block, "html", None)
    return None

def materialize(
    page_builders: list[PageBuilder],
    source_pdf_identifier: str,
    processing_context: NormalizerProcessingContext,
    classified_pages: list[list[Any]],
) -> Document:
    #document_id (computed once)
    document_id = _compute_document_id(source_pdf_identifier)

    sorted_page_builders = sorted(page_builders, key=lambda pb: pb.page_number or 0)

    id_map = _build_marker_id_to_final_id_map(sorted_page_builders, document_id)

    materialized_pages: list[Page] = []

    for pb in sorted_page_builders:
        page_children: list[Any] = []
        for child in pb.children:
            if isinstance(child, SectionBuilder):
                page_children.append(
                    _mat_section_postorder(child, document_id, id_map)
                )
            else:
                page_children.append(
                    _materialize_leaf(child, document_id, id_map)
                )

        page = Page(
            id=_compute_object_id(document_id, pb.canonical_path),
            page_number=pb.page_number,
            is_front_matter=pb.is_front_matter,
            children=page_children,
            provenance=_materialize_provenance(pb.provenance, document_id, id_map),
        )
        materialized_pages.append(page)

    processing_metadata = ProcessingMetadata(
        marker_version=processing_context.marker_version,
        normalizer_version=processing_context.normalizer_version,
        source_marker_artifact_ref=processing_context.source_marker_artifact_ref,
        processed_at=processing_context.processed_at,
    )

    title = _extract_title(sorted_page_builders, classified_pages)

    metadata = Metadata(
        page_count=len(materialized_pages),
        has_front_matter_page=any(p.is_front_matter for p in materialized_pages),
        title=title,
    )

    counts = _count_objects(materialized_pages)
    statistics = Statistics(
        page_count=counts["page_count"],
        section_count=counts["section_count"],
        paragraph_count=counts["paragraph_count"],
        table_count=counts["table_count"],
        figure_count=counts["figure_count"],
        equation_count=counts["equation_count"],
        footnote_count=counts["footnote_count"],
        unresolved_footnote_count=counts["unresolved_footnote_count"],
        reference_count=counts["reference_count"],
    )

    document = Document(
        id=document_id,
        pages=materialized_pages,
        metadata=metadata,
        statistics=statistics,
        processing_metadata=processing_metadata,
        source_pdf_identifier=source_pdf_identifier,
    )

    log_materialization_complete(
        statistics=counts,
        normalizer_version=processing_context.normalizer_version,
    )

    return document