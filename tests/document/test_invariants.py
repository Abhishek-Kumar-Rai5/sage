from __future__ import annotations

import pytest
from pydantic import ValidationError

from betydb_extraction.document import Section

from .conftest import (
    make_document,
    make_page,
    make_paragraph,
    make_reference,
    make_section,
    make_table,
)


class TestEndToEndDeterminism:
    def test_identical_construction_produces_identical_ids(self):
        doc_a = make_document()
        doc_b = make_document()
        assert doc_a.id == doc_b.id
        assert doc_a.pages[0].id == doc_b.pages[0].id

    def test_identical_construction_produces_byte_identical_json(self):
        doc_a = make_document()
        doc_b = make_document()
        assert doc_a.model_dump_json() == doc_b.model_dump_json()

    def test_full_tree_with_reference_is_deterministic(self):
        def build():
            return make_document(
                pages=[
                    make_page(
                        0,
                        children=[
                            make_section(
                                "/page/0/SectionHeader/0",
                                heading_text="References",
                                children=[make_reference(), make_reference("/page/0/ListItem/1")],
                            )
                        ],
                    )
                ]
            )

        doc_a, doc_b = build(), build()
        assert doc_a.model_dump_json() == doc_b.model_dump_json()


class TestImmutabilityDepth:

    def test_top_level_assignment_blocked(self):
        section = make_section()
        with pytest.raises(ValidationError):
            section.depth = 5

    def test_section_children_list_itself_is_not_swappable(self):
        section = make_section(children=[make_paragraph()])
        with pytest.raises(ValidationError):
            section.children = []

    def test_nested_child_object_is_independently_frozen(self):
        para = make_paragraph()
        section = make_section(children=[para])
        # The child retrieved from the parent is the same frozen model;
        # mutating it must still fail.
        with pytest.raises(ValidationError):
            section.children[0].text = "mutated"

    def test_document_pages_list_itself_is_not_swappable(self):
        doc = make_document()
        with pytest.raises(ValidationError):
            doc.pages = []


class TestExtraFieldsForbidden:

    def test_section_rejects_unknown_field(self):
        with pytest.raises(ValidationError):
            Section(
                **{
                    **make_section().model_dump(),
                    "unexpected_field": "should not be allowed",
                }
            )

    def test_table_rejects_unknown_field(self):
        with pytest.raises(ValidationError):
            type(make_table())(
                **{**make_table().model_dump(), "unexpected_field": "x"}
            )

    def test_document_rejects_unknown_field(self):
        with pytest.raises(ValidationError):
            type(make_document())(
                **{**make_document().model_dump(), "unexpected_field": "x"}
            )