"""Tests for Stage 1: Page Builder Construction."""
from __future__ import annotations

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.internal.stage1 import build_page_shells


def _page_block(block_id: str, bbox=None) -> MarkerBlock:
    return MarkerBlock(id=block_id, block_type="Page", bbox=bbox, children=[])


def test_single_page_shell_basic_fields():
    page = _page_block("/page/0/Page/0")
    shells = build_page_shells([page], {})

    assert len(shells) == 1
    shell = shells[0]
    assert shell.page_number == 0
    assert shell.is_front_matter is False
    assert shell.children == []
    assert shell.provenance.marker_block_ids == ["/page/0/Page/0"]
    assert shell.provenance.page_number == 0
    assert shell.provenance.bbox is None
    assert shell.provenance.polygon is None


def test_page_number_is_enumerate_index_not_parsed_from_id():
    page0 = _page_block("/page/5/Page/0")
    page1 = _page_block("/page/1/Page/0")
    shells = build_page_shells([page0, page1], {})

    assert shells[0].page_number == 0
    assert shells[1].page_number == 1
    assert shells[0].provenance.page_number == 0
    assert shells[1].provenance.page_number == 1


def test_bbox_set_when_present():
    page = _page_block("/page/0/Page/0", bbox=[10.0, 20.0, 30.0, 40.0])
    shells = build_page_shells([page], {})

    bbox = shells[0].provenance.bbox
    assert bbox is not None
    assert bbox.x0 == 10.0
    assert bbox.y0 == 20.0
    assert bbox.x1 == 30.0
    assert bbox.y1 == 40.0


def test_bbox_none_when_absent():
    page = _page_block("/page/0/Page/0", bbox=None)
    shells = build_page_shells([page], {})
    assert shells[0].provenance.bbox is None


def test_front_matter_flags_applied_per_index():
    pages = [_page_block(f"/page/{i}/Page/0") for i in range(3)]
    flags = {0: True, 2: True}  # index 1 deliberately omitted
    shells = build_page_shells(pages, flags)

    assert shells[0].is_front_matter is True
    assert shells[1].is_front_matter is False  # default for missing index
    assert shells[2].is_front_matter is True


def test_missing_index_defaults_to_false():
    page = _page_block("/page/0/Page/0")
    shells = build_page_shells([page], {5: True})  # unrelated index
    assert shells[0].is_front_matter is False


def test_multiple_pages_order_and_count():
    pages = [_page_block(f"/page/{i}/Page/0") for i in range(5)]
    shells = build_page_shells(pages, {})

    assert len(shells) == 5
    for i, shell in enumerate(shells):
        assert shell.page_number == i
        assert shell.provenance.marker_block_ids == [f"/page/{i}/Page/0"]


def test_children_always_empty_at_this_stage():
    page = _page_block("/page/0/Page/0")
    shells = build_page_shells([page], {})
    assert shells[0].children == []


def test_empty_page_blocks_returns_empty_list():
    shells = build_page_shells([], {})
    assert shells == []