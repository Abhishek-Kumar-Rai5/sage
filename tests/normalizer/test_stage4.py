"""Tests for Stage 4: Caption Resolution."""
from __future__ import annotations

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.builders.base import (
    ClassifiedBlock,
    Disposition,
    UnwrappedBlock,
    WrapperContext,
)
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.internal.stage4 import resolve_captions


def _block(block_id, block_type, html="", bbox=None):
    return MarkerBlock(id=block_id, block_type=block_type, html=html, bbox=bbox, children=None)


def _cb(block, disposition, wrapper_context=None):
    return ClassifiedBlock(
        unwrapped=UnwrappedBlock(block=block, wrapper_context=wrapper_context),
        disposition=disposition,
    )


def _table_builder(block_id, page_number=0):
    return TableBuilder(
        kind="table",
        raw_html="<table/>",
        caption=None,
        rows=[],
        cells=[],
        footnote_ids=[],
        provenance=ProvenanceBuilder(marker_block_ids=[block_id], page_number=page_number),
        canonical_path=None,
    )


def _figure_builder(block_id, page_number=0):
    return FigureBuilder(
        kind="figure",
        image_data=None,
        caption=None,
        footnote_ids=[],
        provenance=ProvenanceBuilder(marker_block_ids=[block_id], page_number=page_number),
        canonical_path=None,
    )


# Pattern A (wrapped)

def test_pattern_a_table_group_caption_before_table():
    ctx = WrapperContext(wrapper_type="TableGroup", block_id="/p/0/TableGroup/0")
    caption_block = _block("/p/0/Caption/0", "Caption", html="Table 1. My table caption.")
    table_block = _block("/p/0/Table/0", "Table")

    seq = [
        _cb(caption_block, Disposition.CAPTION_TEXT, wrapper_context=ctx),
        _cb(table_block, Disposition.TABLE_SHELL, wrapper_context=ctx),
    ]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)

    assert builder.caption is not None
    assert builder.caption.kind == "caption"
    assert builder.caption.label == "Table 1"
    assert builder.caption.text == "My table caption."
    assert builder.caption.provenance.marker_block_ids == [
        "/p/0/Caption/0", "/p/0/TableGroup/0",
    ]


def test_pattern_a_figure_group_caption_after_figure():
    ctx = WrapperContext(wrapper_type="FigureGroup", block_id="/p/0/FigureGroup/0")
    figure_block = _block("/p/0/Figure/0", "Figure")
    caption_block = _block("/p/0/Caption/0", "Caption", html="Figure 2. My figure caption.")

    seq = [
        _cb(figure_block, Disposition.FIGURE_SHELL, wrapper_context=ctx),
        _cb(caption_block, Disposition.CAPTION_TEXT, wrapper_context=ctx),
    ]
    builder = _figure_builder("/p/0/Figure/0")
    resolve_captions([builder], seq, page_number=0)

    assert builder.caption is not None
    assert builder.caption.label == "Figure 2"
    assert builder.caption.text == "My figure caption."


def test_pattern_a_no_matching_wrapper_sibling_gives_none():
    ctx = WrapperContext(wrapper_type="TableGroup", block_id="/p/0/TableGroup/0")
    table_block = _block("/p/0/Table/0", "Table")
    seq = [_cb(table_block, Disposition.TABLE_SHELL, wrapper_context=ctx)]

    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)
    assert builder.caption is None


# Pattern B (bare)

def test_pattern_b_label_text_shell_resolves():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 3")
    text = _block("/p/0/Text/0", "Text", html="Effect of treatment on yield.")
    table = _block("/p/0/Table/0", "Table")

    seq = [
        _cb(label, Disposition.CAPTION_LABEL),
        _cb(text, Disposition.BODY_PARAGRAPH),
        _cb(table, Disposition.TABLE_SHELL),
    ]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)

    assert builder.caption is not None
    assert builder.caption.label == "Table 3"
    assert builder.caption.text == "Effect of treatment on yield."
    assert builder.caption.trailing_notes is None
    assert builder.caption.provenance.marker_block_ids == [
        "/p/0/SH/0", "/p/0/Text/0",
    ]


def test_pattern_b_trailing_notes_attached():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 3")
    text = _block("/p/0/Text/0", "Text", html="Caption text.")
    table = _block("/p/0/Table/0", "Table")
    notes = _block("/p/0/Text/1", "Text", html="Note: values are means.")

    seq = [
        _cb(label, Disposition.CAPTION_LABEL),
        _cb(text, Disposition.BODY_PARAGRAPH),
        _cb(table, Disposition.TABLE_SHELL),
        _cb(notes, Disposition.BODY_PARAGRAPH),
    ]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)

    assert builder.caption.trailing_notes == "Note: values are means."
    assert builder.caption.provenance.marker_block_ids == [
        "/p/0/SH/0", "/p/0/Text/0", "/p/0/Text/1",
    ]


def test_pattern_b_trailing_notes_case_sensitive_no_match():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 3")
    text = _block("/p/0/Text/0", "Text", html="Caption text.")
    table = _block("/p/0/Table/0", "Table")
    not_notes = _block("/p/0/Text/1", "Text", html="note: lowercase, should not match.")

    seq = [
        _cb(label, Disposition.CAPTION_LABEL),
        _cb(text, Disposition.BODY_PARAGRAPH),
        _cb(table, Disposition.TABLE_SHELL),
        _cb(not_notes, Disposition.BODY_PARAGRAPH),
    ]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)

    assert builder.caption.trailing_notes is None


def test_pattern_b_picture_blocks_transparent():
    label = _block("/p/0/SH/0", "SectionHeader", html="Figure 4")
    pic1 = _block("/p/0/Picture/0", "Picture")
    text = _block("/p/0/Text/0", "Text", html="Figure caption text.")
    pic2 = _block("/p/0/Picture/1", "Picture")
    figure = _block("/p/0/Figure/0", "Figure")

    seq = [
        _cb(label, Disposition.CAPTION_LABEL),
        _cb(pic1, Disposition.PICTURE),
        _cb(text, Disposition.BODY_PARAGRAPH),
        _cb(pic2, Disposition.PICTURE),
        _cb(figure, Disposition.FIGURE_SHELL),
    ]
    builder = _figure_builder("/p/0/Figure/0")
    resolve_captions([builder], seq, page_number=0)

    assert builder.caption is not None
    assert builder.caption.label == "Figure 4"
    assert builder.caption.text == "Figure caption text."


def test_pattern_b_missing_label_gives_none():
    text1 = _block("/p/0/Text/0", "Text", html="Random paragraph.")
    text2 = _block("/p/0/Text/1", "Text", html="Caption-looking text.")
    table = _block("/p/0/Table/0", "Table")

    seq = [
        _cb(text1, Disposition.BODY_PARAGRAPH),
        _cb(text2, Disposition.BODY_PARAGRAPH),
        _cb(table, Disposition.TABLE_SHELL),
    ]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)
    assert builder.caption is None


def test_pattern_b_no_caption_text_immediately_before_shell_gives_none():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 5")
    table = _block("/p/0/Table/0", "Table")

    seq = [
        _cb(label, Disposition.CAPTION_LABEL),
        _cb(table, Disposition.TABLE_SHELL),
    ]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)
    assert builder.caption is None


def test_pattern_b_no_preceding_block_at_all_gives_none():
    table = _block("/p/0/Table/0", "Table")
    seq = [_cb(table, Disposition.TABLE_SHELL)]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)
    assert builder.caption is None


def test_pattern_b_wrong_disposition_before_label_position_gives_none():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 6")
    equation = _block("/p/0/Eq/0", "Equation", html="x=y")
    table = _block("/p/0/Table/0", "Table")

    seq = [
        _cb(label, Disposition.CAPTION_LABEL),
        _cb(equation, Disposition.EQUATION),
        _cb(table, Disposition.TABLE_SHELL),
    ]
    builder = _table_builder("/p/0/Table/0")
    resolve_captions([builder], seq, page_number=0)
    assert builder.caption is None

def test_non_table_figure_builders_ignored():
    from betydb_extraction.normalizer.builders.paragraph import ParagraphBuilder

    para = ParagraphBuilder(
        kind="paragraph",
        text="hi",
        provenance=ProvenanceBuilder(marker_block_ids=["/p/0/Text/0"], page_number=0),
        canonical_path=None,
    )
    seq = [_cb(_block("/p/0/Text/0", "Text"), Disposition.BODY_PARAGRAPH)]
    resolve_captions([para], seq, page_number=0)
    assert not hasattr(para, "caption")


def test_multiple_builders_resolved_independently():
    label1 = _block("/p/0/SH/0", "SectionHeader", html="Table 1")
    text1 = _block("/p/0/Text/0", "Text", html="First caption.")
    table1 = _block("/p/0/Table/0", "Table")

    label2 = _block("/p/0/SH/1", "SectionHeader", html="Table 2")
    text2 = _block("/p/0/Text/1", "Text", html="Second caption.")
    table2 = _block("/p/0/Table/1", "Table")

    seq = [
        _cb(label1, Disposition.CAPTION_LABEL),
        _cb(text1, Disposition.BODY_PARAGRAPH),
        _cb(table1, Disposition.TABLE_SHELL),
        _cb(label2, Disposition.CAPTION_LABEL),
        _cb(text2, Disposition.BODY_PARAGRAPH),
        _cb(table2, Disposition.TABLE_SHELL),
    ]
    b1 = _table_builder("/p/0/Table/0")
    b2 = _table_builder("/p/0/Table/1")
    resolve_captions([b1, b2], seq, page_number=0)

    assert b1.caption.text == "First caption."
    assert b2.caption.text == "Second caption."