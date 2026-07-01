"""Tests for Stage 6: Footnote Attachment."""
from __future__ import annotations

import pytest

from betydb_extraction.marker_adapter.raw_model import MarkerBBox
from betydb_extraction.normalizer.builders.base import ClassifiedBlock, Disposition, UnwrappedBlock
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.footnote import FootnoteBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.internal.stage6 import attach_footnotes
from betydb_extraction.marker_adapter.raw_model import MarkerBlock


def _bbox(y0, y1, x0=0.0, x1=100.0):
    return MarkerBBox(x0=x0, y0=y0, x1=x1, y1=y1)


def _footnote_builder(marker_block_id, bbox=None):
    return FootnoteBuilder(
        kind="footnote",
        raw_text="1. Note.",
        attached_object_id=None,
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id], page_number=0, bbox=bbox),
        canonical_path=None,
    )


def _table_builder(marker_block_id, bbox=None):
    return TableBuilder(
        kind="table",
        raw_html="<table/>",
        caption=None,
        rows=[],
        cells=[],
        footnote_ids=[],
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id], page_number=0, bbox=bbox),
        canonical_path=None,
    )


def _figure_builder(marker_block_id, bbox=None):
    return FigureBuilder(
        kind="figure",
        image_data=None,
        caption=None,
        footnote_ids=[],
        provenance=ProvenanceBuilder(marker_block_ids=[marker_block_id], page_number=0, bbox=bbox),
        canonical_path=None,
    )


def _seq_entry(marker_block_id, block_type="Table"):
    block = MarkerBlock(id=marker_block_id, block_type=block_type, children=None)
    return ClassifiedBlock(
        unwrapped=UnwrappedBlock(block=block, wrapper_context=None),
        disposition=Disposition.TABLE_SHELL,
    )


#Basic attachment

def test_footnote_attaches_to_table_above_it():
    table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=100, y1=200))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [_seq_entry("/p/0/Table/0"), _seq_entry("/p/0/Footnote/0")]

    attach_footnotes([table, footnote], seq, page_number=0)

    assert footnote.attached_object_id == "/p/0/Table/0"
    assert table.footnote_ids == ["/p/0/Footnote/0"]


def test_footnote_attaches_to_figure_above_it():
    figure = _figure_builder("/p/0/Figure/0", bbox=_bbox(y0=100, y1=200))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [_seq_entry("/p/0/Figure/0"), _seq_entry("/p/0/Footnote/0")]

    attach_footnotes([figure, footnote], seq, page_number=0)

    assert footnote.attached_object_id == "/p/0/Figure/0"
    assert figure.footnote_ids == ["/p/0/Footnote/0"]


def test_candidate_below_footnote_not_eligible():
    table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=300, y1=400))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [_seq_entry("/p/0/Table/0"), _seq_entry("/p/0/Footnote/0")]

    attach_footnotes([table, footnote], seq, page_number=0)
    assert footnote.attached_object_id is None
    assert table.footnote_ids == []


def test_equal_y1_and_y0_not_eligible_strict_inequality():
    table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=100, y1=250))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [_seq_entry("/p/0/Table/0"), _seq_entry("/p/0/Footnote/0")]

    attach_footnotes([table, footnote], seq, page_number=0)
    assert footnote.attached_object_id is None


def test_no_candidates_leaves_attached_object_id_none():
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [_seq_entry("/p/0/Footnote/0")]

    attach_footnotes([footnote], seq, page_number=0)
    assert footnote.attached_object_id is None


def test_footnote_missing_bbox_leaves_none():
    table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=100, y1=200))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=None)
    seq = [_seq_entry("/p/0/Table/0"), _seq_entry("/p/0/Footnote/0")]

    attach_footnotes([table, footnote], seq, page_number=0)
    assert footnote.attached_object_id is None
    assert table.footnote_ids == []


def test_candidate_missing_bbox_skipped():
    table_no_bbox = _table_builder("/p/0/Table/0", bbox=None)
    table_with_bbox = _table_builder("/p/0/Table/1", bbox=_bbox(y0=100, y1=200))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [
        _seq_entry("/p/0/Table/0"),
        _seq_entry("/p/0/Table/1"),
        _seq_entry("/p/0/Footnote/0"),
    ]

    attach_footnotes([table_no_bbox, table_with_bbox, footnote], seq, page_number=0)
    assert footnote.attached_object_id == "/p/0/Table/1"


def test_closest_candidate_by_max_y1_selected():
    far_table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=10, y1=50))
    near_table = _table_builder("/p/0/Table/1", bbox=_bbox(y0=100, y1=200))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [
        _seq_entry("/p/0/Table/0"),
        _seq_entry("/p/0/Table/1"),
        _seq_entry("/p/0/Footnote/0"),
    ]

    attach_footnotes([far_table, near_table, footnote], seq, page_number=0)
    assert footnote.attached_object_id == "/p/0/Table/1"


#Tie-break by seq index

def test_tie_break_by_smaller_seq_index():
    table_a = _table_builder("/p/0/Table/0", bbox=_bbox(y0=100, y1=200))
    table_b = _table_builder("/p/0/Table/1", bbox=_bbox(y0=100, y1=200))  # same y1
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))

    # table_b appears earlier in classified_seq than table_a.
    seq = [
        _seq_entry("/p/0/Table/1"),
        _seq_entry("/p/0/Table/0"),
        _seq_entry("/p/0/Footnote/0"),
    ]

    attach_footnotes([table_a, table_b, footnote], seq, page_number=0)
    assert footnote.attached_object_id == "/p/0/Table/1"
    assert table_b.footnote_ids == ["/p/0/Footnote/0"]
    assert table_a.footnote_ids == []


#Multiple footnotes, atomic both-sides update

def test_multiple_footnotes_each_attached_independently():
    table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=100, y1=200))
    fn1 = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    fn2 = _footnote_builder("/p/0/Footnote/1", bbox=_bbox(y0=280, y1=300))
    seq = [
        _seq_entry("/p/0/Table/0"),
        _seq_entry("/p/0/Footnote/0"),
        _seq_entry("/p/0/Footnote/1"),
    ]

    attach_footnotes([table, fn1, fn2], seq, page_number=0)

    assert fn1.attached_object_id == "/p/0/Table/0"
    assert fn2.attached_object_id == "/p/0/Table/0"
    assert set(table.footnote_ids) == {"/p/0/Footnote/0", "/p/0/Footnote/1"}


def test_no_footnotes_no_op():
    table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=100, y1=200))
    seq = [_seq_entry("/p/0/Table/0")]
    attach_footnotes([table], seq, page_number=0)
    assert table.footnote_ids == []


def test_candidate_not_in_classified_seq_raises():
    table = _table_builder("/p/0/Table/0", bbox=_bbox(y0=100, y1=200))
    footnote = _footnote_builder("/p/0/Footnote/0", bbox=_bbox(y0=250, y1=270))
    seq = [_seq_entry("/p/0/Footnote/0")]  # table missing from seq

    with pytest.raises(ValueError):
        attach_footnotes([table, footnote], seq, page_number=0)