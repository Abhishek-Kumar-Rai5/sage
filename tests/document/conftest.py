"""
Shared fixtures and small construction helpers for the Document Object test suite.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from betydb_extraction.document import (
    BoundingBox,
    Caption,
    Document,
    Equation,
    Figure,
    Footnote,
    Metadata,
    NodeKind,
    Page,
    PageFooter,
    PageHeader,
    Paragraph,
    Polygon,
    ProcessingMetadata,
    Reference,
    Section,
    Statistics,
    StructuralProvenance,
    Table,
    TableCell,
    TableRow,
    TableRowCell,
    compute_document_id,
    compute_object_id,
)

TEST_DOCUMENT_ID = compute_document_id("10.1000/test-doi")


def make_provenance(
    canonical_path: str = "/page/0/Text/0",
    *,
    reading_order_index: int = 0,
    page_number: int = 0,
    bbox: BoundingBox | None = None,
    section_path: list[str] | None = None,
) -> StructuralProvenance:
    return StructuralProvenance(
        marker_block_ids=[canonical_path],
        page_number=page_number,
        bbox=bbox,
        reading_order_index=reading_order_index,
        section_path=section_path or [],
    )


def make_id(canonical_path: str) -> str:
    """Compute a deterministic object id rooted at TEST_DOCUMENT_ID."""
    return compute_object_id(TEST_DOCUMENT_ID, canonical_path)


def make_paragraph(path: str = "/page/0/Text/0", text: str = "Body text.") -> Paragraph:
    return Paragraph(
        id=make_id(path),
        text=text,
        provenance=make_provenance(path),
    )


def make_footnote(path: str = "/page/0/Footnote/0") -> Footnote:
    return Footnote(
        id=make_id(path),
        provenance=make_provenance(path),
        raw_text="1. See methods for details.",
    )


def make_reference(path: str = "/page/9/ListItem/0") -> Reference:
    return Reference(
        id=make_id(path),
        provenance=make_provenance(path),
        raw_text="Smukler, S. et al. 2012. Nutrient cycling. J. Agron.",
    )


def make_equation(path: str = "/page/3/Equation/0") -> Equation:
    return Equation(
        id=make_id(path),
        provenance=make_provenance(path),
        raw_math="<math>y = mx + b ... (1)</math>",
    )


def make_caption(path: str = "/page/6/Caption/0") -> Caption:
    return Caption(
        label="Table 3",
        text="Nutrient flux by treatment.",
        provenance=make_provenance(path),
    )


def make_table(path: str = "/page/6/Table/0") -> Table:
    return Table(
        id=make_id(path),
        provenance=make_provenance(path),
        caption=make_caption(),
        raw_html="<table><tr><td>1.2</td></tr></table>",
        rows=[TableRow(cells=[TableRowCell(text="1.2", is_header=False)])],
        cells=[
            TableCell(
                id=make_id(path + "/cell/0"),
                text="1.2",
                bbox=BoundingBox(x0=0, y0=0, x1=10, y1=10),
                polygon=Polygon(
                    points=((0, 0), (10, 0), (10, 10), (0, 10))
                ),
            )
        ],
    )


def make_figure(path: str = "/page/7/Figure/0") -> Figure:
    return Figure(
        id=make_id(path),
        provenance=make_provenance(path),
        caption=make_caption(path + "/Caption/0"),
    )


def make_page_header(path: str = "/page/0/PageHeader/0") -> PageHeader:
    return PageHeader(
        id=make_id(path),
        provenance=make_provenance(path),
        raw_text="J. Agronomic Studies",
    )


def make_page_footer(path: str = "/page/0/PageFooter/0") -> PageFooter:
    return PageFooter(
        id=make_id(path),
        provenance=make_provenance(path),
        raw_text="Page 1 of 12",
    )


def make_section(
    path: str = "/page/0/SectionHeader/0",
    *,
    heading_text: str = "Methods",
    depth: int = 0,
    children: list | None = None,
) -> Section:
    return Section(
        id=make_id(path),
        heading_text=heading_text,
        provenance=make_provenance(path),
        depth=depth,
        children=children or [],
    )


def make_page(
    page_number: int = 0,
    *,
    children: list | None = None,
    is_front_matter: bool = False,
) -> Page:
    path = f"/page/{page_number}"
    return Page(
        id=make_id(path),
        page_number=page_number,
        provenance=make_provenance(path, page_number=page_number),
        children=children or [],
        is_front_matter=is_front_matter,
    )


def make_statistics(**overrides) -> Statistics:
    base = dict(
        page_count=1,
        section_count=1,
        paragraph_count=1,
        table_count=0,
        figure_count=0,
        equation_count=0,
        footnote_count=0,
        reference_count=0,
        unresolved_footnote_count=0,
    )
    base.update(overrides)
    return Statistics(**base)


def make_metadata(**overrides) -> Metadata:
    base = dict(title="A Paper", page_count=1, has_front_matter_page=False)
    base.update(overrides)
    return Metadata(**base)


def make_processing_metadata(**overrides) -> ProcessingMetadata:
    base = dict(
        marker_version="1.2.3",
        normalizer_version="0.1.0",
        processed_at=datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
        source_marker_artifact_ref="artifacts/smukler_2012.marker.json",
    )
    base.update(overrides)
    return ProcessingMetadata(**base)


def make_document(**overrides) -> Document:
    base = dict(
        id=TEST_DOCUMENT_ID,
        source_pdf_identifier="10.1000/test-doi",
        metadata=make_metadata(),
        processing_metadata=make_processing_metadata(),
        statistics=make_statistics(),
        pages=[make_page(0, children=[make_paragraph()])],
    )
    base.update(overrides)
    return Document(**base)