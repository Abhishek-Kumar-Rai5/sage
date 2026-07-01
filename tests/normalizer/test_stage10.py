"""Tests for Stage 10: Materialization."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.builders.base import ClassifiedBlock, Disposition, UnwrappedBlock
from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.context import NormalizerProcessingContext
from betydb_extraction.normalizer.internal.stage3 import build_leaf_builders
from betydb_extraction.normalizer.internal.stage4 import resolve_captions
from betydb_extraction.normalizer.internal.stage5 import build_table_structure
from betydb_extraction.normalizer.internal.stage6 import attach_footnotes
from betydb_extraction.normalizer.internal.stage7 import assemble_section_tree
from betydb_extraction.normalizer.internal.stage8 import assign_reading_order
from betydb_extraction.normalizer.internal.stage9 import compute_canonical_paths
from betydb_extraction.normalizer.internal.stage10 import (
    materialize,
    _compute_document_id,
    _compute_object_id,
)


def _block(block_id, block_type, html="", bbox=None, polygon=None, images=None, section_hierarchy=None):
    return MarkerBlock(
        id=block_id, block_type=block_type, html=html, bbox=bbox, polygon=polygon,
        images=images, section_hierarchy=section_hierarchy or {}, children=None,
    )


def _ctx():
    return NormalizerProcessingContext(
        marker_version="test-marker-1.0",
        normalizer_version="test-normalizer-1.0",
        source_marker_artifact_ref="test/path.json",
        processed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _build_page(page_index, blocks_with_dispositions, is_front_matter=False):
    seq = [
        ClassifiedBlock(unwrapped=UnwrappedBlock(block=b, wrapper_context=None), disposition=d)
        for b, d in blocks_with_dispositions
    ]
    builders = build_leaf_builders(seq, page_number=page_index)
    resolve_captions(builders, seq, page_index)
    build_table_structure(builders, seq)
    attach_footnotes(builders, seq, page_index)
    page_builder = PageBuilder(
        page_number=page_index,
        is_front_matter=is_front_matter,
        provenance=ProvenanceBuilder(
            marker_block_ids=[f"/page/{page_index}/Page/0"], page_number=page_index
        ),
        children=builders,
    )
    return page_builder, seq


def _run_pipeline(pages_spec):
    page_builders, classified_pages = [], []
    for i, (bwd, ifm) in enumerate(pages_spec):
        pb, seq = _build_page(i, bwd, ifm)
        page_builders.append(pb)
        classified_pages.append(seq)

    assemble_section_tree(page_builders, classified_pages)
    assign_reading_order(page_builders)
    compute_canonical_paths(page_builders)
    return page_builders, classified_pages


def test_single_paragraph_document():
    text = _block("/p/0/Text/0", "Text", html="Hello world")
    pages, classified = _run_pipeline([([(text, Disposition.BODY_PARAGRAPH)], False)])

    doc = materialize(pages, "src:1", _ctx(), classified)

    assert doc.source_pdf_identifier == "src:1"
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 0
    assert doc.pages[0].is_front_matter is False
    assert len(doc.pages[0].children) == 1
    para = doc.pages[0].children[0]
    assert para.kind == "paragraph"
    assert para.text == "Hello world"


def test_document_id_matches_compute_document_id():
    text = _block("/p/0/Text/0", "Text", html="x")
    pages, classified = _run_pipeline([([(text, Disposition.BODY_PARAGRAPH)], False)])

    doc = materialize(pages, "src:abc", _ctx(), classified)
    assert doc.id == _compute_document_id("src:abc")


def test_object_id_deterministic_from_canonical_path():
    text = _block("/p/0/Text/0", "Text", html="x")
    pages, classified = _run_pipeline([([(text, Disposition.BODY_PARAGRAPH)], False)])

    doc = materialize(pages, "src:abc", _ctx(), classified)
    para = doc.pages[0].children[0]
    document_id = _compute_document_id("src:abc")
    expected_id = _compute_object_id(document_id, "/page/0/paragraph/1")
    assert para.id == expected_id


def test_different_source_pdf_identifier_gives_different_ids():
    text1 = _block("/p/0/Text/0", "Text", html="x")
    pages1, classified1 = _run_pipeline([([(text1, Disposition.BODY_PARAGRAPH)], False)])
    doc1 = materialize(pages1, "src:one", _ctx(), classified1)

    text2 = _block("/p/0/Text/0", "Text", html="x")
    pages2, classified2 = _run_pipeline([([(text2, Disposition.BODY_PARAGRAPH)], False)])
    doc2 = materialize(pages2, "src:two", _ctx(), classified2)

    assert doc1.id != doc2.id
    assert doc1.pages[0].children[0].id != doc2.pages[0].children[0].id


# Statistics 

def test_statistics_counts_match_content():
    text1 = _block("/p/0/Text/0", "Text", html="a")
    text2 = _block("/p/0/Text/1", "Text", html="b")
    table = _block("/p/0/Table/0", "Table", html="<table></table>")
    figure = _block("/p/0/Figure/0", "Figure")
    equation = _block("/p/0/Eq/0", "Equation", html="x=y")

    blocks = [
        (text1, Disposition.BODY_PARAGRAPH),
        (text2, Disposition.BODY_PARAGRAPH),
        (table, Disposition.TABLE_SHELL),
        (figure, Disposition.FIGURE_SHELL),
        (equation, Disposition.EQUATION),
    ]
    pages, classified = _run_pipeline([(blocks, False)])
    doc = materialize(pages, "src:1", _ctx(), classified)

    stats = doc.statistics
    assert stats.page_count == 1
    assert stats.paragraph_count == 2
    assert stats.table_count == 1
    assert stats.figure_count == 1
    assert stats.equation_count == 1
    assert stats.section_count == 0
    assert stats.footnote_count == 0


def test_metadata_page_count_and_front_matter_flag():
    front_text = _block("/p/0/Text/0", "Text", html="cover")
    body_text = _block("/p/1/Text/0", "Text", html="content")
    pages, classified = _run_pipeline([
        ([(front_text, Disposition.BODY_PARAGRAPH)], True),
        ([(body_text, Disposition.BODY_PARAGRAPH)], False),
    ])
    doc = materialize(pages, "src:1", _ctx(), classified)

    assert doc.metadata.page_count == 2
    assert doc.metadata.has_front_matter_page is True


#Title extraction

def test_title_from_first_heading_on_first_non_front_matter_page():
    front_heading = _block("/p/0/SH/0", "SectionHeader", html="Front Matter Heading")
    front_content = _block(
        "/p/0/Text/0", "Text", html="cover",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    real_heading = _block("/p/1/SH/0", "SectionHeader", html="Real Title")
    real_content = _block(
        "/p/1/Text/0", "Text", html="body",
        section_hierarchy={"0": "/p/1/SH/0"},
    )
    pages, classified = _run_pipeline([
        ([(front_heading, Disposition.GENUINE_SECTION_HEADER), (front_content, Disposition.BODY_PARAGRAPH)], True),
        ([(real_heading, Disposition.GENUINE_SECTION_HEADER), (real_content, Disposition.BODY_PARAGRAPH)], False),
    ])
    doc = materialize(pages, "src:1", _ctx(), classified)

    assert doc.metadata.title == "Real Title"


def test_title_none_when_no_heading_present():
    text = _block("/p/0/Text/0", "Text", html="no headers here")
    pages, classified = _run_pipeline([([(text, Disposition.BODY_PARAGRAPH)], False)])
    doc = materialize(pages, "src:1", _ctx(), classified)
    assert doc.metadata.title is None


#Section materialization

def test_section_materialized_with_children():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Intro")
    para = _block(
        "/p/0/Text/0", "Text", html="body",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    blocks = [(heading, Disposition.GENUINE_SECTION_HEADER), (para, Disposition.BODY_PARAGRAPH)]
    pages, classified = _run_pipeline([(blocks, False)])
    doc = materialize(pages, "src:1", _ctx(), classified)

    section = doc.pages[0].children[0]
    assert section.kind == "section"
    assert section.heading_text == "Intro"
    assert section.depth == 0
    assert len(section.children) == 1
    assert section.children[0].text == "body"


def test_leaf_section_path_translated_to_final_section_id():
    heading = _block("/p/0/SH/0", "SectionHeader", html="Intro")
    para = _block(
        "/p/0/Text/0", "Text", html="body",
        section_hierarchy={"0": "/p/0/SH/0"},
    )
    blocks = [(heading, Disposition.GENUINE_SECTION_HEADER), (para, Disposition.BODY_PARAGRAPH)]
    pages, classified = _run_pipeline([(blocks, False)])
    doc = materialize(pages, "src:1", _ctx(), classified)

    section = doc.pages[0].children[0]
    leaf = section.children[0]
    assert leaf.provenance.section_path == [section.id]


#Footnote <-> Table symmetric translation

def test_footnote_table_ids_translated_and_symmetric():
    table = _block("/p/0/Table/0", "Table", html="<table></table>", bbox=[0, 0, 10, 50])
    footnote = _block("/p/0/Footnote/0", "Footnote", html="1. note", bbox=[0, 60, 10, 70])
    blocks = [(table, Disposition.TABLE_SHELL), (footnote, Disposition.FOOTNOTE)]
    pages, classified = _run_pipeline([(blocks, False)])
    doc = materialize(pages, "src:1", _ctx(), classified)

    mat_table = doc.pages[0].children[0]
    mat_footnote = doc.pages[0].children[1]

    assert mat_footnote.attached_object_id == mat_table.id
    assert mat_table.footnote_ids == [mat_footnote.id]


def test_footnote_unresolved_stays_none_and_counted():
    footnote = _block("/p/0/Footnote/0", "Footnote", html="1. orphan note")
    blocks = [(footnote, Disposition.FOOTNOTE)]
    pages, classified = _run_pipeline([(blocks, False)])
    doc = materialize(pages, "src:1", _ctx(), classified)

    mat_footnote = doc.pages[0].children[0]
    assert mat_footnote.attached_object_id is None
    assert doc.statistics.unresolved_footnote_count == 1


#Table row/cell text and empty-cell handling

def test_table_row_cell_empty_text_becomes_empty_string_not_none():
    table = _block("/p/0/Table/0", "Table", html="<table><tr><td></td></tr></table>")
    blocks = [(table, Disposition.TABLE_SHELL)]
    pages, classified = _run_pipeline([(blocks, False)])
    doc = materialize(pages, "src:1", _ctx(), classified)

    mat_table = doc.pages[0].children[0]
    assert mat_table.rows[0].cells[0].text == ""


#BoundingBox / Polygon conversion

def test_bbox_and_polygon_converted_on_materialized_provenance():
    text = _block(
        "/p/0/Text/0", "Text", html="x",
        bbox=[1.0, 2.0, 3.0, 4.0],
        polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
    )
    blocks = [(text, Disposition.BODY_PARAGRAPH)]
    pages, classified = _run_pipeline([(blocks, False)])
    doc = materialize(pages, "src:1", _ctx(), classified)

    prov = doc.pages[0].children[0].provenance
    assert prov.bbox.x0 == 1.0
    assert prov.bbox.y1 == 4.0
    assert prov.polygon.points == ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))





#ProcessingMetadata passthrough

def test_processing_metadata_passed_verbatim():
    text = _block("/p/0/Text/0", "Text", html="x")
    pages, classified = _run_pipeline([([(text, Disposition.BODY_PARAGRAPH)], False)])
    ctx = _ctx()
    doc = materialize(pages, "src:1", ctx, classified)

    pm = doc.processing_metadata
    assert pm.marker_version == ctx.marker_version
    assert pm.normalizer_version == ctx.normalizer_version
    assert pm.source_marker_artifact_ref == ctx.source_marker_artifact_ref
    assert pm.processed_at == ctx.processed_at


def test_dangling_footnote_reference_raises():
    footnote = _block("/p/0/Footnote/0", "Footnote", html="orphan")
    blocks = [(footnote, Disposition.FOOTNOTE)]
    pages, classified = _run_pipeline([(blocks, False)])

    footnote_builder = pages[0].children[0]
    footnote_builder.attached_object_id = "/does/not/exist"

    with pytest.raises(ValueError):
        materialize(pages, "src:1", _ctx(), classified)