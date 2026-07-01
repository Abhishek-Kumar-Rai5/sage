"""Tests for Statistics (Spec Section 7), Metadata (Spec Section 5), and
ProcessingMetadata (Spec Section 6).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from betydb_extraction.document import Metadata, ProcessingMetadata, Statistics

from .conftest import make_metadata, make_processing_metadata, make_statistics


class TestStatistics:
    def test_minimal_valid_construction(self):
        stats = make_statistics()
        assert stats.page_count == 1

    def test_all_counts_must_be_non_negative(self):
        for field in [
            "page_count",
            "section_count",
            "paragraph_count",
            "table_count",
            "figure_count",
            "equation_count",
            "footnote_count",
            "reference_count",
            "unresolved_footnote_count",
        ]:
            with pytest.raises(ValidationError):
                make_statistics(**{field: -1})

    def test_unresolved_cannot_exceed_total_footnotes(self):
        with pytest.raises(ValidationError):
            make_statistics(footnote_count=2, unresolved_footnote_count=3)

    def test_unresolved_equal_to_total_is_valid(self):
        stats = make_statistics(footnote_count=2, unresolved_footnote_count=2)
        assert stats.unresolved_footnote_count == 2

    def test_unresolved_less_than_total_is_valid(self):
        stats = make_statistics(footnote_count=5, unresolved_footnote_count=2)
        assert stats.unresolved_footnote_count == 2

    def test_reference_count_field_exists(self):
        # Direct regression guard for the original v1.0 omission this
        # whole correction was about: Statistics always had this field,
        # and it must still be present and independently settable.
        stats = make_statistics(reference_count=7)
        assert stats.reference_count == 7

    def test_is_frozen(self):
        stats = make_statistics()
        with pytest.raises(ValidationError):
            stats.page_count = 99


class TestMetadata:
    def test_minimal_valid_construction(self):
        meta = make_metadata()
        assert meta.page_count == 1

    def test_title_optional(self):
        meta = Metadata(page_count=1, has_front_matter_page=False)
        assert meta.title is None

    def test_page_count_non_negative(self):
        with pytest.raises(ValidationError):
            make_metadata(page_count=-1)

    def test_has_no_author_journal_year_doi_fields(self):
        # Spec 5's boundary note: these are explicitly NOT modeled here.
        for forbidden_field in ["author", "authors", "journal", "year", "doi"]:
            assert forbidden_field not in Metadata.model_fields

    def test_is_frozen(self):
        meta = make_metadata()
        with pytest.raises(ValidationError):
            meta.title = "Different Title"


class TestProcessingMetadata:
    def test_minimal_valid_construction(self):
        pm = make_processing_metadata()
        assert pm.marker_version == "1.2.3"

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValidationError):
            make_processing_metadata(processed_at=datetime(2026, 6, 17, 12, 0, 0))

    def test_non_utc_offset_rejected(self):
        offset_tz = timezone(timedelta(hours=5))
        with pytest.raises(ValidationError):
            make_processing_metadata(
                processed_at=datetime(2026, 6, 17, 12, 0, 0, tzinfo=offset_tz)
            )

    def test_utc_datetime_accepted(self):
        pm = make_processing_metadata(
            processed_at=datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
        )
        assert pm.processed_at.tzinfo is not None

    def test_processed_at_not_part_of_any_id(self):
        # Spec 6: processed_at is explicitly excluded from id computation.
        # This is really a Document/identifiers-level guarantee, but we
        # confirm here that ProcessingMetadata itself exposes no id field
        # derived from processed_at.
        assert "id" not in ProcessingMetadata.model_fields

    def test_is_frozen(self):
        pm = make_processing_metadata()
        with pytest.raises(ValidationError):
            pm.marker_version = "9.9.9"