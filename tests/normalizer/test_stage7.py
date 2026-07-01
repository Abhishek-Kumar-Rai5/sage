"""Tests for Stage 7: Section Tree Assembly."""
from __future__ import annotations

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.builders.base import (
    ClassifiedBlock,
    Disposition,
    UnwrappedBlock,
)
from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.page_footer import PageFooterBuilder
from betydb_extraction.normalizer.builders.page_header import PageHeaderBuilder
from betydb_extraction.normalizer.builders.paragraph import ParagraphBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.section import SectionBuilder
from betydb_extraction.normalizer.internal.stage3 import build_leaf_builders
from betydb_extraction.normalizer.internal.stage7 import assemble_section_tree


def _block(block_id, block_type, html="", section_hierarchy=None):
    return MarkerBlock(
        id=block_id,
        block_type=block_type,
        html=html,
        section_hierarchy=section_hierarchy or {},
        children=None,
    )


def _make_page(blocks_with_dispositions, page_index):
    seq = [
        ClassifiedBlock(
            unwrapped=UnwrappedBlock(block=b, wrapper_context=None),
            disposition=d,
        )
        for b, d in blocks_with_dispositions
    ]
    builders = build_leaf_builders(seq, page_number=page_index)
    page_builder = PageBuilder(
        page_number=page_index,
        is_front_matter=False,
        provenance=ProvenanceBuilder(
            marker_block_ids=[f"/page/{page_index}/Page/0"], page_number=page_index
        ),
        children=builders,
    )
    return page_builder, seq


def test_no_headings_leaves_children_untouched():
    text = _block("/p/0/Text/0", "Text", html="hello")
    pb, seq = _make_page([(text, Disposition.BODY_PARAGRAPH)], page_index=0)
    original_children = list(pb.children)

    assemble_section_tree([pb], [seq])

    assert pb.children == original_children
    assert pb.children[0].provenance.section_path == []


#Single top-level section

def test_single_top_level_section_with_content():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Intro")
    para = _block(
        "/p/0/Text/0", "Text", html="body",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    pb, seq = _make_page(
        [(heading, Disposition.GENUINE_SECTION_HEADER), (para, Disposition.BODY_PARAGRAPH)],
        page_index=0,
    )

    assemble_section_tree([pb], [seq])

    assert len(pb.children) == 1
    section = pb.children[0]
    assert isinstance(section, SectionBuilder)
    assert section.kind == "section"
    assert section.depth == 0
    assert section.heading_text == "Intro"
    assert section.heading_marker_block_id == "/p/0/SH/0"
    assert section.provenance.section_path == []

    assert len(section.children) == 1
    para_builder = section.children[0]
    assert isinstance(para_builder, ParagraphBuilder)
    assert para_builder.provenance.section_path == ["/p/0/SH/0"]


# Nested sections

def test_nested_two_level_sections():
    h0 = _block("/p/0/SH/0", "SectionHeader", html="Parent")
    h1 = _block("/p/0/SH/1", "SectionHeader", html="Child")
    content = _block(
        "/p/0/Text/0", "Text", html="deep content",
        section_hierarchy={"0": "/p/0/SH/0", "1": "/p/0/SH/1"},
    )
    pb, seq = _make_page(
        [
            (h0, Disposition.GENUINE_SECTION_HEADER),
            (h1, Disposition.GENUINE_SECTION_HEADER),
            (content, Disposition.BODY_PARAGRAPH),
        ],
        page_index=0,
    )

    assemble_section_tree([pb], [seq])

    assert len(pb.children) == 1
    parent_section = pb.children[0]
    assert parent_section.heading_marker_block_id == "/p/0/SH/0"
    assert parent_section.depth == 0
    assert parent_section.provenance.section_path == []

    assert len(parent_section.children) == 1
    child_section = parent_section.children[0]
    assert isinstance(child_section, SectionBuilder)
    assert child_section.heading_marker_block_id == "/p/0/SH/1"
    assert child_section.depth == 1
    assert child_section.provenance.section_path == ["/p/0/SH/0"]

    assert len(child_section.children) == 1
    leaf = child_section.children[0]
    assert leaf.provenance.section_path == ["/p/0/SH/0", "/p/0/SH/1"]


# Omission rule

def test_heading_with_no_governed_content_is_omitted():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Empty Section")
    ungoverned = _block("/p/0/Text/0", "Text", html="not in any section")
    pb, seq = _make_page(
        [
            (heading, Disposition.GENUINE_SECTION_HEADER),
            (ungoverned, Disposition.BODY_PARAGRAPH),
        ],
        page_index=0,
    )

    assemble_section_tree([pb], [seq])

    assert len(pb.children) == 1
    assert isinstance(pb.children[0], ParagraphBuilder)
    assert pb.children[0].provenance.section_path == []


# Multi-page section spanning

def test_section_spans_pages_content_attached_to_heading_page():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Methods")
    page0, seq0 = _make_page([(heading, Disposition.GENUINE_SECTION_HEADER)], page_index=0)

    content = _block(
        "/p/1/Text/0", "Text", html="continued on next page",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    page1, seq1 = _make_page([(content, Disposition.BODY_PARAGRAPH)], page_index=1)

    assemble_section_tree([page0, page1], [seq0, seq1])

    assert len(page0.children) == 1
    section = page0.children[0]
    assert isinstance(section, SectionBuilder)

    assert page1.children == []
    assert len(section.children) == 1
    assert section.children[0].provenance.marker_block_ids == ["/p/1/Text/0"]
    assert section.children[0].provenance.section_path == ["/p/0/SH/0"]


#PageHeader / PageFooter always page-level 

def test_page_header_forced_to_page_level_even_if_governed():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Section")
    header = _block(
        "/p/0/PH/0", "PageHeader", html="Journal Name",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    para = _block(
        "/p/0/Text/0", "Text", html="content",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    pb, seq = _make_page(
        [
            (heading, Disposition.GENUINE_SECTION_HEADER),
            (header, Disposition.PAGE_HEADER),
            (para, Disposition.BODY_PARAGRAPH),
        ],
        page_index=0,
    )

    assemble_section_tree([pb], [seq])
    header_builders = [b for b in pb.children if isinstance(b, PageHeaderBuilder)]
    assert len(header_builders) == 1
    assert header_builders[0].provenance.section_path == []

    section = [b for b in pb.children if isinstance(b, SectionBuilder)][0]
    assert all(not isinstance(c, PageHeaderBuilder) for c in section.children)
    assert len(section.children) == 1  # only the paragraph


def test_page_footer_forced_to_page_level():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Section")
    footer = _block(
        "/p/0/PF/0", "PageFooter", html="Page 1",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    para = _block(
        "/p/0/Text/0", "Text", html="content",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    pb, seq = _make_page(
        [
            (heading, Disposition.GENUINE_SECTION_HEADER),
            (footer, Disposition.PAGE_FOOTER),
            (para, Disposition.BODY_PARAGRAPH),
        ],
        page_index=0,
    )

    assemble_section_tree([pb], [seq])

    footer_builders = [b for b in pb.children if isinstance(b, PageFooterBuilder)]
    assert len(footer_builders) == 1
    assert footer_builders[0].provenance.section_path == []


# Ordering (Step 6)

def test_children_ordered_by_classified_sequence_position():
    text_before = _block("/p/0/Text/0", "Text", html="before section")
    heading = _block("/p/0/SH/0", "SectionHeader", html="Section")
    para = _block(
        "/p/0/Text/1", "Text", html="inside",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    pb, seq = _make_page(
        [
            (text_before, Disposition.BODY_PARAGRAPH),
            (heading, Disposition.GENUINE_SECTION_HEADER),
            (para, Disposition.BODY_PARAGRAPH),
        ],
        page_index=0,
    )

    assemble_section_tree([pb], [seq])

    assert len(pb.children) == 2
    assert isinstance(pb.children[0], ParagraphBuilder)
    assert pb.children[0].provenance.marker_block_ids == ["/p/0/Text/0"]
    assert isinstance(pb.children[1], SectionBuilder)


def test_two_top_level_sections_ordered_by_heading_position():
    h_second_in_doc = _block("/p/0/SH/0", "SectionHeader", html="First Heading")
    para1 = _block(
        "/p/0/Text/0", "Text", html="p1",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    h_second = _block("/p/0/SH/1", "SectionHeader", html="Second Heading")
    para2 = _block(
        "/p/0/Text/1", "Text", html="p2",
        section_hierarchy={"0": "/p/0/SH/1"},
    )
    pb, seq = _make_page(
        [
            (h_second_in_doc, Disposition.GENUINE_SECTION_HEADER),
            (para1, Disposition.BODY_PARAGRAPH),
            (h_second, Disposition.GENUINE_SECTION_HEADER),
            (para2, Disposition.BODY_PARAGRAPH),
        ],
        page_index=0,
    )

    assemble_section_tree([pb], [seq])

    assert len(pb.children) == 2
    assert pb.children[0].heading_marker_block_id == "/p/0/SH/0"
    assert pb.children[1].heading_marker_block_id == "/p/0/SH/1"


#Invariant sanity

def test_section_builder_heading_id_matches_provenance_marker_block_ids():
    heading = _block("/p/0/SH/0", "SectionHeader", html="X")
    para = _block(
        "/p/0/Text/0", "Text", html="y",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    pb, seq = _make_page(
        [(heading, Disposition.GENUINE_SECTION_HEADER), (para, Disposition.BODY_PARAGRAPH)],
        page_index=0,
    )
    assemble_section_tree([pb], [seq])

    section = pb.children[0]
    assert section.heading_marker_block_id == section.provenance.marker_block_ids[0]