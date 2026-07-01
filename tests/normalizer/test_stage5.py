"""Tests for Stage 5: Table Internal Structure."""
from __future__ import annotations

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.builders.base import (
    ClassifiedBlock,
    Disposition,
    UnwrappedBlock,
    WrapperContext,
)
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.internal.stage5 import build_table_structure


def _table_builder(raw_html, marker_block_id="/p/0/Table/0"):
    return TableBuilder(
        kind="table",
        raw_html=raw_html,
        caption=None,
        rows=[],
        cells=[],
        footnote_ids=[],
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id], page_number=0),
        canonical_path=None,
    )


def _shell_block(block_id, bbox=None):
    return MarkerBlock(id=block_id, block_type="Table", bbox=bbox, children=None)


def _cell_evidence_block(block_id, html, bbox=None):
    return MarkerBlock(id=block_id, block_type="TableCell", html=html, bbox=bbox, children=None)


def _cb(block, disposition, wrapper_context=None):
    return ClassifiedBlock(
        unwrapped=UnwrappedBlock(block=block, wrapper_context=wrapper_context),
        disposition=disposition,
    )


def test_empty_raw_html_gives_empty_rows():
    builder = _table_builder(raw_html="")
    build_table_structure([builder], [])
    assert builder.rows == []


def test_whitespace_only_raw_html_gives_empty_rows():
    builder = _table_builder(raw_html="   \n  ")
    build_table_structure([builder], [])
    assert builder.rows == []


def test_simple_table_parses_rows_and_cells():
    html = "<table><tr><th>Name</th><td>Value</td></tr></table>"
    builder = _table_builder(raw_html=html)
    build_table_structure([builder], [])

    assert len(builder.rows) == 1
    row = builder.rows[0]
    assert row.kind == "table_row"
    assert len(row.cells) == 2

    header_cell, data_cell = row.cells
    assert header_cell.kind == "table_row_cell"
    assert header_cell.text == "Name"
    assert header_cell.is_header is True
    assert header_cell.structural_notes is None

    assert data_cell.text == "Value"
    assert data_cell.is_header is False


def test_multiple_rows_preserved_in_order():
    html = (
        "<table>"
        "<tr><td>R1C1</td></tr>"
        "<tr><td>R2C1</td></tr>"
        "<tr><td>R3C1</td></tr>"
        "</table>"
    )
    builder = _table_builder(raw_html=html)
    build_table_structure([builder], [])

    assert len(builder.rows) == 3
    assert [r.cells[0].text for r in builder.rows] == ["R1C1", "R2C1", "R3C1"]


def test_empty_cell_text_becomes_none():
    html = "<table><tr><td></td></tr></table>"
    builder = _table_builder(raw_html=html)
    build_table_structure([builder], [])
    assert builder.rows[0].cells[0].text is None


def test_math_wrapper_stripped_inner_content_preserved():
    html = (
        "<table><tr><td>"
        "<math><mi>x</mi><mo>=</mo><mn>2</mn></math>"
        "</td></tr></table>"
    )
    builder = _table_builder(raw_html=html)
    build_table_structure([builder], [])

    cell_text = builder.rows[0].cells[0].text
    assert "<math" not in cell_text
    assert "</math>" not in cell_text
    assert "<mi>x</mi>" in cell_text
    assert "<mo>=</mo>" in cell_text
    assert "<mn>2</mn>" in cell_text


def test_math_wrapper_mixed_with_plain_text():
    html = (
        "<table><tr><td>"
        "Result: <math><mn>5</mn></math> units"
        "</td></tr></table>"
    )
    builder = _table_builder(raw_html=html)
    build_table_structure([builder], [])
    text = builder.rows[0].cells[0].text
    assert text == "Result: <mn>5</mn> units"


def test_bare_table_cells_always_empty():
    builder = _table_builder(raw_html="<table><tr><td>x</td></tr></table>")
    shell = _shell_block("/p/0/Table/0")
    seq = [_cb(shell, Disposition.TABLE_SHELL, wrapper_context=None)]

    build_table_structure([builder], seq)
    assert builder.cells == []


def test_wrapped_table_collects_matching_evidence_cells():
    ctx = WrapperContext(wrapper_type="TableGroup", block_id="/p/0/TableGroup/0")
    shell = _shell_block("/p/0/Table/0")
    ev1 = _cell_evidence_block("/p/0/TableCell/0", html="Alpha")
    ev2 = _cell_evidence_block("/p/0/TableCell/1", html="Beta")

    seq = [
        _cb(ev1, Disposition.TABLE_CELL_EVIDENCE, wrapper_context=ctx),
        _cb(shell, Disposition.TABLE_SHELL, wrapper_context=ctx),
        _cb(ev2, Disposition.TABLE_CELL_EVIDENCE, wrapper_context=ctx),
    ]
    builder = _table_builder(raw_html="<table></table>")
    build_table_structure([builder], seq)

    assert len(builder.cells) == 2
    assert builder.cells[0].kind == "table_cell"
    assert builder.cells[0].marker_block_id == "/p/0/TableCell/0"
    assert builder.cells[0].text == "Alpha"
    assert builder.cells[1].text == "Beta"


def test_wrapped_table_evidence_text_not_math_stripped():
    ctx = WrapperContext(wrapper_type="TableGroup", block_id="/p/0/TableGroup/0")
    shell = _shell_block("/p/0/Table/0")
    ev = _cell_evidence_block("/p/0/TableCell/0", html="<math><mn>5</mn></math>")

    seq = [
        _cb(shell, Disposition.TABLE_SHELL, wrapper_context=ctx),
        _cb(ev, Disposition.TABLE_CELL_EVIDENCE, wrapper_context=ctx),
    ]
    builder = _table_builder(raw_html="<table></table>")
    build_table_structure([builder], seq)

    assert builder.cells[0].text == "<math><mn>5</mn></math>"


def test_evidence_cells_from_other_wrapper_id_excluded():
    ctx_this = WrapperContext(wrapper_type="TableGroup", block_id="/p/0/TableGroup/0")
    ctx_other = WrapperContext(wrapper_type="TableGroup", block_id="/p/0/TableGroup/1")
    shell = _shell_block("/p/0/Table/0")
    ev_this = _cell_evidence_block("/p/0/TableCell/0", html="Mine")
    ev_other = _cell_evidence_block("/p/0/TableCell/1", html="NotMine")

    seq = [
        _cb(shell, Disposition.TABLE_SHELL, wrapper_context=ctx_this),
        _cb(ev_this, Disposition.TABLE_CELL_EVIDENCE, wrapper_context=ctx_this),
        _cb(ev_other, Disposition.TABLE_CELL_EVIDENCE, wrapper_context=ctx_other),
    ]
    builder = _table_builder(raw_html="<table></table>")
    build_table_structure([builder], seq)

    assert len(builder.cells) == 1
    assert builder.cells[0].text == "Mine"


def test_evidence_cell_bbox_and_polygon_carried():
    ctx = WrapperContext(wrapper_type="TableGroup", block_id="/p/0/TableGroup/0")
    shell = _shell_block("/p/0/Table/0")
    ev = _cell_evidence_block(
        "/p/0/TableCell/0", html="X", bbox=[1.0, 2.0, 3.0, 4.0]
    )
    seq = [
        _cb(shell, Disposition.TABLE_SHELL, wrapper_context=ctx),
        _cb(ev, Disposition.TABLE_CELL_EVIDENCE, wrapper_context=ctx),
    ]
    builder = _table_builder(raw_html="<table></table>")
    build_table_structure([builder], seq)

    assert builder.cells[0].bbox.x0 == 1.0

def test_non_table_builders_ignored():
    from betydb_extraction.normalizer.builders.paragraph import ParagraphBuilder

    para = ParagraphBuilder(
        kind="paragraph",
        text="hi",
        provenance=ProvenanceBuilder(marker_block_ids=["/p/0/Text/0"], page_number=0),
        canonical_path=None,
    )
    build_table_structure([para], [])
    assert not hasattr(para, "rows")


def test_shell_not_in_classified_seq_defaults_to_bare():
    builder = _table_builder(raw_html="<table><tr><td>x</td></tr></table>")
    build_table_structure([builder], [])
    assert builder.cells == []
    assert len(builder.rows) == 1