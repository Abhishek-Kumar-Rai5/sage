"""Tests for Stage 2: Block Classification."""
from __future__ import annotations

import pytest

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.builders.base import Disposition, UnwrappedBlock
from betydb_extraction.normalizer.errors import UnrecognizedBlockTypeError
from betydb_extraction.normalizer.internal.stage2 import classify_blocks


def _block(block_id, block_type, html="", section_hierarchy=None, children=None):
    return MarkerBlock(
        id=block_id,
        block_type=block_type,
        html=html,
        section_hierarchy=section_hierarchy or {},
        children=children,
    )


def _u(block):
    return UnwrappedBlock(block=block, wrapper_context=None)

@pytest.mark.parametrize(
    "block_type,expected",
    [
        ("Text", Disposition.BODY_PARAGRAPH),
        ("Table", Disposition.TABLE_SHELL),
        ("Figure", Disposition.FIGURE_SHELL),
        ("Caption", Disposition.CAPTION_TEXT),
        ("TableCell", Disposition.TABLE_CELL_EVIDENCE),
        ("Equation", Disposition.EQUATION),
        ("Footnote", Disposition.FOOTNOTE),
        ("PageHeader", Disposition.PAGE_HEADER),
        ("PageFooter", Disposition.PAGE_FOOTER),
        ("Picture", Disposition.PICTURE),
    ],
)
def test_static_dispatch(block_type, expected):
    block = _block("/p/0/X/0", block_type)
    result = classify_blocks([_u(block)], page_index=0)
    assert result[0].disposition == expected


def test_unrecognized_block_type_raises():
    block = _block("/p/0/Weird/0", "WeirdUnknownType")
    with pytest.raises(UnrecognizedBlockTypeError):
        classify_blocks([_u(block)], page_index=0)


def test_section_header_default_genuine():
    block = _block("/p/0/SH/0", "SectionHeader", html="Introduction")
    result = classify_blocks([_u(block)], page_index=0)
    assert result[0].disposition == Disposition.GENUINE_SECTION_HEADER


def test_section_header_caption_label_override_table():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 3")
    table = _block("/p/0/Table/0", "Table")
    result = classify_blocks([_u(label), _u(table)], page_index=0)
    assert result[0].disposition == Disposition.CAPTION_LABEL


def test_section_header_caption_label_override_figure_with_margin():
    # Pattern B: label, then a Text block, then the Figure (within window=3)
    label = _block("/p/0/SH/0", "SectionHeader", html="Figure 12.")
    filler = _block("/p/0/Text/0", "Text", html="some filler")
    figure = _block("/p/0/Figure/0", "Figure")
    result = classify_blocks([_u(label), _u(filler), _u(figure)], page_index=0)
    assert result[0].disposition == Disposition.CAPTION_LABEL


def test_section_header_text_matches_but_no_table_figure_nearby_stays_genuine():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 3")
    filler1 = _block("/p/0/Text/0", "Text")
    filler2 = _block("/p/0/Text/1", "Text")
    filler3 = _block("/p/0/Text/2", "Text")
    result = classify_blocks(
        [_u(label), _u(filler1), _u(filler2), _u(filler3)], page_index=0
    )
    assert result[0].disposition == Disposition.GENUINE_SECTION_HEADER


def test_section_header_table_present_but_text_does_not_match_regex():
    label = _block("/p/0/SH/0", "SectionHeader", html="Introduction")
    table = _block("/p/0/Table/0", "Table")
    result = classify_blocks([_u(label), _u(table)], page_index=0)
    assert result[0].disposition == Disposition.GENUINE_SECTION_HEADER


def test_caption_label_regex_case_insensitive():
    label = _block("/p/0/SH/0", "SectionHeader", html="TABLE 1:")
    table = _block("/p/0/Table/0", "Table")
    result = classify_blocks([_u(label), _u(table)], page_index=0)
    assert result[0].disposition == Disposition.CAPTION_LABEL


def test_caption_label_lookahead_window_boundary():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 3")
    f1 = _block("/p/0/Text/0", "Text")
    f2 = _block("/p/0/Text/1", "Text")
    table = _block("/p/0/Table/0", "Table")  # 3rd block after label (in-window)
    result = classify_blocks([_u(label), _u(f1), _u(f2), _u(table)], page_index=0)
    assert result[0].disposition == Disposition.CAPTION_LABEL


def test_caption_label_lookahead_window_out_of_range_stays_genuine():
    label = _block("/p/0/SH/0", "SectionHeader", html="Table 3")
    f1 = _block("/p/0/Text/0", "Text")
    f2 = _block("/p/0/Text/1", "Text")
    f3 = _block("/p/0/Text/2", "Text")
    table = _block("/p/0/Table/0", "Table")  # 4th block after label — out of window
    result = classify_blocks(
        [_u(label), _u(f1), _u(f2), _u(f3), _u(table)], page_index=0
    )
    assert result[0].disposition == Disposition.GENUINE_SECTION_HEADER

def test_list_item_no_section_hierarchy_is_body_paragraph():
    item = _block("/p/0/LI/0", "ListItem", section_hierarchy={})
    result = classify_blocks([_u(item)], page_index=0)
    assert result[0].disposition == Disposition.BODY_PARAGRAPH


def test_list_item_under_references_heading_is_reference_entry():
    heading = _block("/p/0/SH/0", "SectionHeader", html="References")
    item = _block("/p/0/LI/0", "ListItem", section_hierarchy={"1": "/p/0/SH/0"})
    result = classify_blocks([_u(heading), _u(item)], page_index=0)
    assert result[0].disposition == Disposition.GENUINE_SECTION_HEADER
    assert result[1].disposition == Disposition.REFERENCE_ENTRY


@pytest.mark.parametrize(
    "heading_text",
    ["References", "BIBLIOGRAPHY", "Works Cited", "literature cited"],
)
def test_list_item_references_vocabulary_case_insensitive(heading_text):
    heading = _block("/p/0/SH/0", "SectionHeader", html=heading_text)
    item = _block("/p/0/LI/0", "ListItem", section_hierarchy={"1": "/p/0/SH/0"})
    result = classify_blocks([_u(heading), _u(item)], page_index=0)
    assert result[1].disposition == Disposition.REFERENCE_ENTRY


def test_list_item_under_non_references_heading_is_body_paragraph():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Methods")
    item = _block("/p/0/LI/0", "ListItem", section_hierarchy={"1": "/p/0/SH/0"})
    result = classify_blocks([_u(heading), _u(item)], page_index=0)
    assert result[1].disposition == Disposition.BODY_PARAGRAPH


def test_list_item_deepest_key_resolved_numerically():
    shallow_heading = _block("/p/0/SH/0", "SectionHeader", html="Methods")
    deep_heading = _block("/p/0/SH/1", "SectionHeader", html="References")
    item = _block(
        "/p/0/LI/0", "ListItem",
        section_hierarchy={"2": "/p/0/SH/0", "10": "/p/0/SH/1"},
    )
    result = classify_blocks(
        [_u(shallow_heading), _u(deep_heading), _u(item)], page_index=0
    )
    assert result[2].disposition == Disposition.REFERENCE_ENTRY


def test_list_item_heading_not_yet_seen_is_body_paragraph():
    item = _block("/p/0/LI/0", "ListItem", section_hierarchy={"1": "/p/0/SH/999"})
    result = classify_blocks([_u(item)], page_index=0)
    assert result[0].disposition == Disposition.BODY_PARAGRAPH

def test_heading_registry_shared_across_pages_for_references_split():
    shared_registry: dict = {}
    heading = _block("/p/0/SH/0", "SectionHeader", html="References")
    page0 = classify_blocks([_u(heading)], page_index=0, heading_registry=shared_registry)
    assert page0[0].disposition == Disposition.GENUINE_SECTION_HEADER

    # Page 1's ListItem refers back to page 0's heading id.
    item = _block("/p/1/LI/0", "ListItem", section_hierarchy={"1": "/p/0/SH/0"})
    page1 = classify_blocks([_u(item)], page_index=1, heading_registry=shared_registry)
    assert page1[0].disposition == Disposition.REFERENCE_ENTRY


def test_none_heading_registry_creates_fresh_dict_isolated():
    heading = _block("/p/0/SH/0", "SectionHeader", html="References")
    item = _block("/p/0/LI/0", "ListItem", section_hierarchy={"1": "/p/0/SH/0"})
    result = classify_blocks([_u(heading), _u(item)], page_index=0)
    assert result[1].disposition == Disposition.REFERENCE_ENTRY


def test_result_same_length_and_order_as_input():
    blocks = [
        _u(_block("/p/0/Text/0", "Text")),
        _u(_block("/p/0/Table/0", "Table")),
        _u(_block("/p/0/Figure/0", "Figure")),
    ]
    result = classify_blocks(blocks, page_index=0)
    assert len(result) == 3
    assert [r.unwrapped.block.block_type for r in result] == ["Text", "Table", "Figure"]


def test_empty_sequence_returns_empty_list():
    assert classify_blocks([], page_index=0) == []