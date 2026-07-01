"""Tests for Stage 3: Leaf Builder Construction."""
from __future__ import annotations

import base64

import pytest

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.builders.base import ClassifiedBlock, Disposition, UnwrappedBlock
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.footnote import FootnoteBuilder
from betydb_extraction.normalizer.builders.page_footer import PageFooterBuilder
from betydb_extraction.normalizer.builders.page_header import PageHeaderBuilder
from betydb_extraction.normalizer.builders.paragraph import ParagraphBuilder
from betydb_extraction.normalizer.builders.reference import ReferenceBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.internal.stage3 import build_leaf_builders


def _block(block_id, block_type, html="", bbox=None, polygon=None, images=None):
    return MarkerBlock(
        id=block_id,
        block_type=block_type,
        html=html,
        bbox=bbox,
        polygon=polygon,
        images=images,
        children=None,
    )


def _cb(block, disposition):
    return ClassifiedBlock(
        unwrapped=UnwrappedBlock(block=block, wrapper_context=None),
        disposition=disposition,
    )


def test_body_paragraph_builds_paragraph_builder():
    block = _block("/p/0/Text/0", "Text", html="<p>Hello</p>")
    result = build_leaf_builders([_cb(block, Disposition.BODY_PARAGRAPH)], page_number=2)

    assert len(result) == 1
    b = result[0]
    assert isinstance(b, ParagraphBuilder)
    assert b.kind == "paragraph"
    assert b.text == "<p>Hello</p>"
    assert b.canonical_path is None
    assert b.provenance.marker_block_ids == ["/p/0/Text/0"]
    assert b.provenance.page_number == 2
    assert b.provenance.reading_order_index is None
    assert b.provenance.section_path == []


def test_equation_builds_equation_builder():
    block = _block("/p/0/Equation/0", "Equation", html="x=y")
    result = build_leaf_builders([_cb(block, Disposition.EQUATION)], page_number=0)

    b = result[0]
    assert b.kind == "equation"
    assert b.raw_math == "x=y"
    assert b.equation_number is None


def test_footnote_builds_footnote_builder():
    block = _block("/p/0/Footnote/0", "Footnote", html="1. Note text")
    result = build_leaf_builders([_cb(block, Disposition.FOOTNOTE)], page_number=0)

    b = result[0]
    assert isinstance(b, FootnoteBuilder)
    assert b.kind == "footnote"
    assert b.raw_text == "1. Note text"
    assert b.attached_object_id is None


def test_reference_entry_builds_reference_builder():
    block = _block("/p/0/LI/0", "ListItem", html="Smith, J. (2020).")
    result = build_leaf_builders([_cb(block, Disposition.REFERENCE_ENTRY)], page_number=0)

    b = result[0]
    assert isinstance(b, ReferenceBuilder)
    assert b.kind == "reference"
    assert b.raw_text == "Smith, J. (2020)."


def test_page_header_builds_page_header_builder():
    block = _block("/p/0/PH/0", "PageHeader", html="Journal Name")
    result = build_leaf_builders([_cb(block, Disposition.PAGE_HEADER)], page_number=3)

    b = result[0]
    assert isinstance(b, PageHeaderBuilder)
    assert b.kind == "page_header"
    assert b.raw_text == "Journal Name"


def test_page_footer_builds_page_footer_builder():
    block = _block("/p/0/PF/0", "PageFooter", html="Page 3 of 10")
    result = build_leaf_builders([_cb(block, Disposition.PAGE_FOOTER)], page_number=3)

    b = result[0]
    assert isinstance(b, PageFooterBuilder)
    assert b.kind == "page_footer"
    assert b.raw_text == "Page 3 of 10"


def test_table_shell_builds_table_builder_with_empty_defaults():
    block = _block("/p/0/Table/0", "Table", html="<table>...</table>")
    result = build_leaf_builders([_cb(block, Disposition.TABLE_SHELL)], page_number=0)

    b = result[0]
    assert isinstance(b, TableBuilder)
    assert b.kind == "table"
    assert b.raw_html == "<table>...</table>"
    assert b.caption is None
    assert b.rows == []
    assert b.cells == []
    assert b.footnote_ids == []


def test_figure_shell_builds_figure_builder_defaults():
    block = _block("/p/0/Figure/0", "Figure", html="<img/>")
    result = build_leaf_builders([_cb(block, Disposition.FIGURE_SHELL)], page_number=0)

    b = result[0]
    assert isinstance(b, FigureBuilder)
    assert b.kind == "figure"
    assert b.caption is None
    assert b.footnote_ids == []


#image_data extraction

def test_figure_image_data_decodes_base64_string():
    payload = base64.b64encode(b"raw-bytes-here").decode()
    block = _block("/p/0/Figure/0", "Figure", images={"img1.png": payload})
    result = build_leaf_builders([_cb(block, Disposition.FIGURE_SHELL)], page_number=0)
    assert result[0].image_data == b"raw-bytes-here"


def test_figure_image_data_none_when_images_empty():
    block = _block("/p/0/Figure/0", "Figure", images={})
    result = build_leaf_builders([_cb(block, Disposition.FIGURE_SHELL)], page_number=0)
    assert result[0].image_data is None


def test_figure_image_data_none_when_images_absent():
    block = _block("/p/0/Figure/0", "Figure", images=None)
    result = build_leaf_builders([_cb(block, Disposition.FIGURE_SHELL)], page_number=0)
    assert result[0].image_data is None



#Proveance population

def test_provenance_bbox_and_polygon_carried_from_block():
    block = _block(
        "/p/0/Text/0", "Text", html="hi",
        bbox=[1.0, 2.0, 3.0, 4.0],
        polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
    )
    result = build_leaf_builders([_cb(block, Disposition.BODY_PARAGRAPH)], page_number=0)
    prov = result[0].provenance
    assert prov.bbox.x0 == 1.0
    assert prov.polygon[0].x == 0.0
    assert len(prov.polygon) == 4


@pytest.mark.parametrize(
    "disposition",
    [
        Disposition.CAPTION_TEXT,
        Disposition.TABLE_CELL_EVIDENCE,
        Disposition.GENUINE_SECTION_HEADER,
        Disposition.CAPTION_LABEL,
        Disposition.PICTURE,
    ],
)
def test_no_builder_dispositions_produce_nothing(disposition):
    block = _block("/p/0/X/0", "Caption", html="ignored")
    result = build_leaf_builders([_cb(block, disposition)], page_number=0)
    assert result == []


#Ordering / mixed sequence

def test_order_preserved_and_skipped_blocks_excluded():
    text = _block("/p/0/Text/0", "Text", html="body")
    caption = _block("/p/0/Caption/0", "Caption", html="skip me")
    table = _block("/p/0/Table/0", "Table", html="<table/>")

    seq = [
        _cb(text, Disposition.BODY_PARAGRAPH),
        _cb(caption, Disposition.CAPTION_TEXT),
        _cb(table, Disposition.TABLE_SHELL),
    ]
    result = build_leaf_builders(seq, page_number=0)

    assert len(result) == 2
    assert result[0].kind == "paragraph"
    assert result[1].kind == "table"


def test_empty_sequence_returns_empty_list():
    assert build_leaf_builders([], page_number=0) == []