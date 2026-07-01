"""Tests for betydb_extraction.document.identifiers.
"""
from __future__ import annotations

import pytest

from betydb_extraction.document.identifiers import (
    compute_document_id,
    compute_object_id,
    is_valid_document_id,
    is_valid_object_id,
    validate_document_id_shape,
    validate_object_id_shape,
)


class TestDeterminism:
    def test_document_id_is_deterministic(self):
        assert compute_document_id("10.1000/x") == compute_document_id("10.1000/x")

    def test_document_id_differs_for_different_input(self):
        assert compute_document_id("10.1000/x") != compute_document_id("10.1000/y")

    def test_object_id_is_deterministic(self):
        doc_id = compute_document_id("10.1000/x")
        assert compute_object_id(doc_id, "/page/0/Text/0") == compute_object_id(
            doc_id, "/page/0/Text/0"
        )

    def test_object_id_differs_by_canonical_path(self):
        doc_id = compute_document_id("10.1000/x")
        assert compute_object_id(doc_id, "/page/0/Text/0") != compute_object_id(
            doc_id, "/page/0/Text/1"
        )

    def test_object_id_differs_by_document_id(self):
        doc_a = compute_document_id("10.1000/x")
        doc_b = compute_document_id("10.1000/y")
        assert compute_object_id(doc_a, "/page/0/Text/0") != compute_object_id(
            doc_b, "/page/0/Text/0"
        )


class TestShape:
    def test_document_id_has_expected_prefix_and_length(self):
        value = compute_document_id("10.1000/x")
        assert value.startswith("betydoc:")
        assert len(value) == len("betydoc:") + 16

    def test_object_id_has_expected_prefix_and_length(self):
        value = compute_object_id(compute_document_id("10.1000/x"), "/page/0")
        assert value.startswith("doc:")
        assert len(value) == len("doc:") + 16

    def test_is_valid_document_id_accepts_well_formed(self):
        assert is_valid_document_id(compute_document_id("10.1000/x"))

    def test_is_valid_document_id_rejects_object_id(self):
        doc_id = compute_document_id("10.1000/x")
        obj_id = compute_object_id(doc_id, "/page/0")
        assert not is_valid_document_id(obj_id)

    def test_is_valid_object_id_rejects_document_id(self):
        doc_id = compute_document_id("10.1000/x")
        assert not is_valid_object_id(doc_id)

    @pytest.mark.parametrize(
        "bad_value",
        [
            "betydoc:short",
            "betydoc:" + "g" * 16,  # non-hex char
            "wrongprefix:" + "a" * 16,
            "",
        ],
    )
    def test_is_valid_document_id_rejects_malformed(self, bad_value):
        assert not is_valid_document_id(bad_value)

    @pytest.mark.parametrize(
        "bad_value",
        [
            "doc:short",
            "doc:" + "G" * 16,  # uppercase not allowed
            "wrongprefix:" + "a" * 16,
            "",
        ],
    )
    def test_is_valid_object_id_rejects_malformed(self, bad_value):
        assert not is_valid_object_id(bad_value)


class TestRaisingValidators:
    def test_validate_document_id_shape_returns_value_when_valid(self):
        value = compute_document_id("10.1000/x")
        assert validate_document_id_shape(value) == value

    def test_validate_document_id_shape_raises_when_invalid(self):
        with pytest.raises(ValueError):
            validate_document_id_shape("not-a-valid-id")

    def test_validate_object_id_shape_returns_value_when_valid(self):
        doc_id = compute_document_id("10.1000/x")
        value = compute_object_id(doc_id, "/page/0")
        assert validate_object_id_shape(value) == value

    def test_validate_object_id_shape_raises_when_invalid(self):
        with pytest.raises(ValueError):
            validate_object_id_shape("not-a-valid-id")