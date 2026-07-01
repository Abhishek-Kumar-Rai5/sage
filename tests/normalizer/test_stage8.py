"""Tests for Stage 8: Global Reading-Order Assignment."""
from __future__ import annotations

from betydb_extraction.normalizer.builders.caption import CaptionBuilder
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.paragraph import ParagraphBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.section import SectionBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.internal.stage8 import assign_reading_order


def _para(marker_block_id="/p/0/Text/0"):
    return ParagraphBuilder(
        kind="paragraph",
        text="hi",
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id]),
        canonical_path=None,
    )


def _table(marker_block_id="/p/0/Table/0", caption=None):
    return TableBuilder(
        kind="table",
        raw_html="<table/>",
        caption=caption,
        rows=[],
        cells=[],
        footnote_ids=[],
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id]),
        canonical_path=None,
    )


def _figure(marker_block_id="/p/0/Figure/0", caption=None):
    return FigureBuilder(
        kind="figure",
        image_data=None,
        caption=caption,
        footnote_ids=[],
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id]),
        canonical_path=None,
    )


def _caption(marker_block_id="/p/0/Caption/0"):
    return CaptionBuilder(
        kind="caption",
        label="Table 1",
        text="A caption",
        trailing_notes=None,
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id]),
        canonical_path=None,
    )


def _section(heading_id="/p/0/SH/0", children=None):
    return SectionBuilder(
        kind="section",
        heading_text="Heading",
        depth=0,
        heading_marker_block_id=heading_id,
        provenance=ProvenanceBuilder(marker_block_ids=[heading_id]),
        children=children if children is not None else [],
    )


def _page(page_number, children=None):
    return PageBuilder(
        page_number=page_number,
        is_front_matter=False,
        provenance=ProvenanceBuilder(marker_block_ids=[f"/page/{page_number}/Page/0"], page_number=page_number),
        children=children if children is not None else [],
    )


# Basic single-page traversal

def test_single_leaf_gets_sequential_indices():
    para = _para()
    page = _page(0, children=[para])

    assign_reading_order([page])

    assert page.provenance.reading_order_index == 0
    assert para.provenance.reading_order_index == 1


def test_multiple_leaves_sequential_in_order():
    p1, p2, p3 = _para("/a"), _para("/b"), _para("/c")
    page = _page(0, children=[p1, p2, p3])

    assign_reading_order([page])

    assert page.provenance.reading_order_index == 0
    assert p1.provenance.reading_order_index == 1
    assert p2.provenance.reading_order_index == 2
    assert p3.provenance.reading_order_index == 3


#Nested sections

def test_section_recursion_before_siblings():
    inner_para = _para("/inner")
    section = _section(children=[inner_para])
    after_para = _para("/after")
    page = _page(0, children=[section, after_para])

    assign_reading_order([page])

    assert page.provenance.reading_order_index == 0
    assert section.provenance.reading_order_index == 1
    assert inner_para.provenance.reading_order_index == 2
    assert after_para.provenance.reading_order_index == 3


def test_nested_two_level_sections():
    leaf = _para("/leaf")
    inner_section = _section(heading_id="/inner_sh", children=[leaf])
    outer_section = _section(heading_id="/outer_sh", children=[inner_section])
    page = _page(0, children=[outer_section])

    assign_reading_order([page])

    assert page.provenance.reading_order_index == 0
    assert outer_section.provenance.reading_order_index == 1
    assert inner_section.provenance.reading_order_index == 2
    assert leaf.provenance.reading_order_index == 3


# Caption handling

def test_table_with_caption_assigns_caption_index_after_table():
    caption = _caption()
    table = _table(caption=caption)
    page = _page(0, children=[table])

    assign_reading_order([page])

    assert page.provenance.reading_order_index == 0
    assert table.provenance.reading_order_index == 1
    assert caption.provenance.reading_order_index == 2


def test_figure_with_caption_assigns_caption_index_after_figure():
    caption = _caption()
    figure = _figure(caption=caption)
    page = _page(0, children=[figure])

    assign_reading_order([page])

    assert figure.provenance.reading_order_index == 1
    assert caption.provenance.reading_order_index == 2


def test_table_without_caption_no_error_no_extra_index():
    table = _table(caption=None)
    after = _para("/after")
    page = _page(0, children=[table, after])

    assign_reading_order([page])

    assert table.provenance.reading_order_index == 1
    assert after.provenance.reading_order_index == 2  # no gap for missing caption


def test_caption_between_table_and_next_sibling():
    caption = _caption()
    table = _table(caption=caption)
    next_para = _para("/next")
    page = _page(0, children=[table, next_para])

    assign_reading_order([page])

    assert table.provenance.reading_order_index == 1
    assert caption.provenance.reading_order_index == 2
    assert next_para.provenance.reading_order_index == 3


#Multi-page: shared counter, sorted by page_number─

def test_counter_shared_and_continues_across_pages():
    p0_para = _para("/p0")
    p1_para = _para("/p1")
    page0 = _page(0, children=[p0_para])
    page1 = _page(1, children=[p1_para])

    assign_reading_order([page0, page1])

    assert page0.provenance.reading_order_index == 0
    assert p0_para.provenance.reading_order_index == 1
    assert page1.provenance.reading_order_index == 2
    assert p1_para.provenance.reading_order_index == 3


def test_pages_processed_in_page_number_order_regardless_of_input_order():
    p0_para = _para("/p0")
    p1_para = _para("/p1")
    page0 = _page(0, children=[p0_para])
    page1 = _page(1, children=[p1_para])

    # Deliberately pass out of order.
    assign_reading_order([page1, page0])

    assert page0.provenance.reading_order_index < page1.provenance.reading_order_index
    assert p0_para.provenance.reading_order_index < p1_para.provenance.reading_order_index



def test_all_assigned_indices_unique_and_strictly_increasing():
    leaf1 = _para("/a")
    section = _section(children=[_para("/b"), _para("/c")])
    leaf2 = _para("/d")
    page0 = _page(0, children=[leaf1, section, leaf2])
    page1 = _page(1, children=[_para("/e")])

    assign_reading_order([page0, page1])

    all_builders = [page0, leaf1, section, *section.children, leaf2, page1, *page1.children]
    indices = [b.provenance.reading_order_index for b in all_builders]

    assert all(i is not None for i in indices)
    assert indices == sorted(indices)
    assert len(set(indices)) == len(indices)