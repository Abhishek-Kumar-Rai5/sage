"""Tests for Document (Spec Section 4): the root container."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from betydb_extraction.document import Document, StructuralProvenance

from .conftest import make_document, make_page, make_paragraph


class TestDocument:
    def test_minimal_valid_construction(self):
        doc = make_document()
        assert len(doc.pages) == 1

    def test_pages_must_be_non_empty(self):
        with pytest.raises(ValidationError):
            make_document(pages=[])

    def test_duplicate_page_numbers_rejected(self):
        with pytest.raises(ValidationError):
            make_document(
                pages=[
                    make_page(0, children=[make_paragraph()]),
                    make_page(0, children=[make_paragraph("/page/0/Text/1")]),
                ]
            )

    def test_out_of_order_pages_rejected(self):
        with pytest.raises(ValidationError):
            make_document(
                pages=[
                    make_page(1, children=[make_paragraph("/page/1/Text/0")]),
                    make_page(0, children=[make_paragraph("/page/0/Text/0")]),
                ]
            )

    def test_ascending_pages_with_gap_is_valid(self):
        # Spec: a Marker-side page omission is preserved, not silently
        # re-numbered -- a gap in page_number is allowed as long as the
        # list itself is still ascending.
        doc = make_document(
            pages=[
                make_page(0, children=[make_paragraph("/page/0/Text/0")]),
                make_page(2, children=[make_paragraph("/page/2/Text/0")]),
            ]
        )
        assert [p.page_number for p in doc.pages] == [0, 2]

    def test_multiple_ascending_pages_valid(self):
        doc = make_document(
            pages=[
                make_page(0, children=[make_paragraph("/page/0/Text/0")]),
                make_page(1, children=[make_paragraph("/page/1/Text/0")]),
                make_page(2, children=[make_paragraph("/page/2/Text/0")]),
            ]
        )
        assert len(doc.pages) == 3

    def test_document_has_no_structural_provenance_field(self):
        # Spec 4 invariant: Document is the only object with no
        # StructuralProvenance of its own.
        assert "provenance" not in Document.model_fields
        for field in Document.model_fields.values():
            assert field.annotation is not StructuralProvenance

    def test_rejects_malformed_document_id(self):
        with pytest.raises(ValidationError):
            make_document(id="not-a-document-id")

    def test_rejects_object_id_shape_as_document_id(self):
        # A doc: id (object-shaped) must not validate as a Document id.
        from betydb_extraction.document.identifiers import compute_object_id

        bad_id = compute_object_id("betydoc:" + "a" * 16, "/page/0")
        with pytest.raises(ValidationError):
            make_document(id=bad_id)

    def test_is_frozen(self):
        doc = make_document()
        with pytest.raises(ValidationError):
            doc.source_pdf_identifier = "different"