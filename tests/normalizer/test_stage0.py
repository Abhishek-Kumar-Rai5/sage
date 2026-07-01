"""Tests for Stage 0: Front-Matter Detection."""
from __future__ import annotations

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.internal.stage0 import detect_front_matter


def _text_block(html: str) -> MarkerBlock:
    return MarkerBlock(block_type="Text", html=html, children=None)


def _section_header() -> MarkerBlock:
    return MarkerBlock(block_type="SectionHeader", html="<h1>Intro</h1>", children=None)


def _page(children: list[MarkerBlock]) -> MarkerBlock:
    return MarkerBlock(block_type="Page", children=children)


def test_no_signals_is_not_front_matter():
    page = _page([_text_block("Regular body text."), _section_header()])
    flags = detect_front_matter([page])
    assert flags == {0: False}


def test_only_s4_is_not_front_matter():
    # No SectionHeader (S4 fires) but no text signals -> only 1 signal total.
    page = _page([_text_block("Just some ordinary text with no headers.")])
    flags = detect_front_matter([page])
    assert flags[0] is False


def test_s1_alone_is_not_front_matter():
    page = _page([_text_block("Submit your article here."), _section_header()])
    flags = detect_front_matter([page])
    assert flags[0] is False


def test_s1_plus_s4_is_front_matter():
    # S1 fires (string present) + S4 fires (no SectionHeader) = 2 signals.
    page = _page([_text_block("Submit your article here.")])
    flags = detect_front_matter([page])
    assert flags[0] is True


def test_s2_plus_s3_is_front_matter():
    page = _page([
        _text_block("ISSN 1234-5678"),
        _text_block("Article views: 42"),
        _section_header(),
    ])
    flags = detect_front_matter([page])
    assert flags[0] is True


def test_s1_case_sensitive():
    # Lowercase variant should NOT match S1 (case-sensitive per spec).
    page = _page([_text_block("submit your article here.")])
    flags = detect_front_matter([page])
    # Only S4 fires (no SectionHeader) -> 1 signal -> not front matter.
    assert flags[0] is False


def test_s4_checked_on_raw_children_not_nested():
    wrapper = MarkerBlock(
        block_type="ListGroup",
        children=[_section_header()],
    )
    page = _page([_text_block("Submit your article here."), wrapper])
    flags = detect_front_matter([page])
    assert flags[0] is True


def test_multiple_pages_all_indices_present():
    front_page = _page([_text_block("Submit your article here.")])
    normal_page = _page([_text_block("Body text."), _section_header()])
    flags = detect_front_matter([front_page, normal_page, normal_page])
    assert flags == {0: True, 1: False, 2: False}


def test_text_concatenation_ignores_non_text_blocks():
    # ISSN pattern lives inside a non-"Text" block_type -> should not count.
    page = _page([
        MarkerBlock(block_type="Caption", html="ISSN 1234-5678", children=None),
        _text_block("Submit your article here."),
    ])
    flags = detect_front_matter([page])
    assert flags[0] is True