"""Tests for Stage 9: Canonical Path Computation."""
from __future__ import annotations

import pytest

from betydb_extraction.normalizer.builders.caption import CaptionBuilder
from betydb_extraction.normalizer.builders.equation import EquationBuilder
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.footnote import FootnoteBuilder
from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.page_footer import PageFooterBuilder
from betydb_extraction.normalizer.builders.page_header import PageHeaderBuilder
from betydb_extraction.normalizer.builders.paragraph import ParagraphBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.reference import ReferenceBuilder
from betydb_extraction.normalizer.builders.section import SectionBuilder
from betydb_extraction.normalizer.builders.table import (
    TableBuilder,
    TableCellBuilder,
    TableRowBuilder,
    TableRowCellBuilder,
)
from betydb_extraction.normalizer.internal.stage9 import compute_canonical_paths


def _prov(marker_block_ids, page_number=0, roi=None, section_path=None):
    return ProvenanceBuilder(
        marker_block_ids=marker_block_ids,
        page_number=page_number,
        reading_order_index=roi,
        section_path=section_path or [],
    )


def _page(page_number, children=None):
    return PageBuilder(
        page_number=page_number,
        is_front_matter=False,
        provenance=_prov([f"/page/{page_number}/Page/0"], page_number=page_number, roi=0),
        children=children if children is not None else [],
    )


def _para(mbid, page_number=0, roi=1):
    return ParagraphBuilder(
        kind="paragraph", text="x",
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _equation(mbid, page_number=0, roi=1):
    return EquationBuilder(
        kind="equation", raw_math="x=y", equation_number=None,
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _footnote(mbid, page_number=0, roi=1):
    return FootnoteBuilder(
        kind="footnote", raw_text="note", attached_object_id=None,
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _reference(mbid, page_number=0, roi=1):
    return ReferenceBuilder(
        kind="reference", raw_text="ref",
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _page_header(mbid, page_number=0, roi=1):
    return PageHeaderBuilder(
        kind="page_header", raw_text="hdr",
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _page_footer(mbid, page_number=0, roi=1):
    return PageFooterBuilder(
        kind="page_footer", raw_text="ftr",
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _table(mbid, page_number=0, roi=1, rows=None, cells=None, caption=None):
    return TableBuilder(
        kind="table", raw_html="<table/>", caption=caption,
        rows=rows or [], cells=cells or [], footnote_ids=[],
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _figure(mbid, page_number=0, roi=1, caption=None):
    return FigureBuilder(
        kind="figure", image_data=None, caption=caption, footnote_ids=[],
        provenance=_prov([mbid], page_number=page_number, roi=roi),
        canonical_path=None,
    )


def _caption(mbid="/p/0/Caption/0"):
    return CaptionBuilder(
        kind="caption", label="Table 1", text="A caption", trailing_notes=None,
        provenance=_prov([mbid]),
        canonical_path=None,
    )


def _section(heading_id, page_number=0, children=None):
    return SectionBuilder(
        kind="section", heading_text="H", depth=0,
        heading_marker_block_id=heading_id,
        provenance=_prov([heading_id], page_number=page_number),
        children=children if children is not None else [],
    )


def _row(cells=None):
    return TableRowBuilder(kind="table_row", cells=cells or [], canonical_path=None)


def _row_cell(text="x", is_header=False):
    return TableRowCellBuilder(
        kind="table_row_cell", text=text, is_header=is_header,
        structural_notes=None, canonical_path=None,
    )


def _flat_cell(mbid, text="x"):
    return TableCellBuilder(
        kind="table_cell", marker_block_id=mbid, text=text,
        bbox=None, polygon=None, canonical_path=None,
    )


def test_page_canonical_path():
    page = _page(3)
    compute_canonical_paths([page])
    assert page.canonical_path == "/page/3"


def test_paragraph_uses_reading_order_index():
    page = _page(0, children=[_para("/p/0/Text/0", roi=5)])
    compute_canonical_paths([page])
    assert page.children[0].canonical_path == "/page/0/paragraph/5"


def test_equation_uses_reading_order_index():
    page = _page(0, children=[_equation("/p/0/Eq/0", roi=7)])
    compute_canonical_paths([page])
    assert page.children[0].canonical_path == "/page/0/equation/7"


def test_reference_uses_reading_order_index():
    page = _page(0, children=[_reference("/p/0/LI/0", roi=9)])
    compute_canonical_paths([page])
    assert page.children[0].canonical_path == "/page/0/reference/9"


def test_footnote_uses_marker_block_id():
    page = _page(0, children=[_footnote("/p/0/Footnote/0")])
    compute_canonical_paths([page])
    assert page.children[0].canonical_path == "/page/0/footnote//p/0/Footnote/0"


def test_page_header_uses_marker_block_id():
    page = _page(0, children=[_page_header("/p/0/PH/0")])
    compute_canonical_paths([page])
    assert page.children[0].canonical_path == "/page/0/page_header//p/0/PH/0"


def test_page_footer_uses_marker_block_id():
    page = _page(0, children=[_page_footer("/p/0/PF/0")])
    compute_canonical_paths([page])
    assert page.children[0].canonical_path == "/page/0/page_footer//p/0/PF/0"


def test_table_path_and_row_cell_paths():
    row = _row(cells=[_row_cell("a"), _row_cell("b")])
    table = _table("/p/0/Table/0", rows=[row])
    page = _page(0, children=[table])
    compute_canonical_paths([page])

    assert table.canonical_path == "/page/0/table//p/0/Table/0"
    assert row.canonical_path == "/page/0/table//p/0/Table/0/row/0"
    assert row.cells[0].canonical_path == "/page/0/table//p/0/Table/0/row/0/cell/0"
    assert row.cells[1].canonical_path == "/page/0/table//p/0/Table/0/row/0/cell/1"


def test_table_flat_cell_evidence_path():
    flat_cell = _flat_cell("/p/0/TableCell/0")
    table = _table("/p/0/Table/0", cells=[flat_cell])
    page = _page(0, children=[table])
    compute_canonical_paths([page])

    assert flat_cell.canonical_path == "/page/0/table//p/0/Table/0/cell_evidence//p/0/TableCell/0"


def test_table_caption_path_and_section_path_copied():
    caption = _caption()
    table = _table("/p/0/Table/0", caption=caption)
    table.provenance.section_path = ["/p/0/SH/0"]
    page = _page(0, children=[table])
    compute_canonical_paths([page])

    assert caption.canonical_path == "/page/0/table//p/0/Table/0/caption"
    assert caption.provenance.section_path == ["/p/0/SH/0"]


def test_figure_caption_path():
    caption = _caption("/p/0/Caption/1")
    figure = _figure("/p/0/Figure/0", caption=caption)
    figure.provenance.section_path = ["/p/0/SH/1"]
    page = _page(0, children=[figure])
    compute_canonical_paths([page])

    assert figure.canonical_path == "/page/0/figure//p/0/Figure/0"
    assert caption.canonical_path == "/page/0/figure//p/0/Figure/0/caption"
    assert caption.provenance.section_path == ["/p/0/SH/1"]


def test_figure_no_caption_no_error():
    figure = _figure("/p/0/Figure/0", caption=None)
    page = _page(0, children=[figure])
    compute_canonical_paths([page])
    assert figure.canonical_path == "/page/0/figure//p/0/Figure/0"


def test_section_path_uses_own_page_number():
    section = _section("/p/0/SH/0", page_number=0)
    page = _page(0, children=[section])
    compute_canonical_paths([page])
    assert section.canonical_path == "/page/0/section//p/0/SH/0"


def test_leaf_inside_section_uses_own_page_number_not_sections():
    leaf = _para("/p/1/Text/0", page_number=1, roi=2)
    section = _section("/p/0/SH/0", page_number=0, children=[leaf])
    page0 = _page(0, children=[section])
    page1 = _page(1, children=[])

    compute_canonical_paths([page0, page1])

    assert section.canonical_path == "/page/0/section//p/0/SH/0"
    assert leaf.canonical_path == "/page/1/paragraph/2"


def test_nested_sections_each_get_own_path():
    inner_leaf = _para("/p/0/Text/0", roi=3)
    inner_section = _section("/p/0/SH/1", children=[inner_leaf])
    outer_section = _section("/p/0/SH/0", children=[inner_section])
    page = _page(0, children=[outer_section])

    compute_canonical_paths([page])

    assert outer_section.canonical_path == "/page/0/section//p/0/SH/0"
    assert inner_section.canonical_path == "/page/0/section//p/0/SH/1"
    assert inner_leaf.canonical_path == "/page/0/paragraph/3"


# Missing prerequisites raise

def test_missing_reading_order_index_raises():
    para = _para("/p/0/Text/0", roi=None)
    page = _page(0, children=[para])
    with pytest.raises(ValueError):
        compute_canonical_paths([page])


def test_missing_marker_block_ids_raises():
    footnote = _footnote("/p/0/Footnote/0")
    footnote.provenance.marker_block_ids = []
    page = _page(0, children=[footnote])
    with pytest.raises(ValueError):
        compute_canonical_paths([page])


# Multi-page ordering

def test_pages_processed_in_page_number_order():
    page0 = _page(0, children=[_para("/p/0/Text/0", page_number=0, roi=1)])
    page1 = _page(1, children=[_para("/p/1/Text/0", page_number=1, roi=1)])

    compute_canonical_paths([page1, page0])  # deliberately out of order

    assert page0.canonical_path == "/page/0"
    assert page1.canonical_path == "/page/1"
    assert page0.children[0].canonical_path == "/page/0/paragraph/1"
    assert page1.children[0].canonical_path == "/page/1/paragraph/1"