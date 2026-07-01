"""Serialization tests per Spec invariant 1.5 and Section 19:
"""
from __future__ import annotations

import base64

from betydb_extraction.document import Figure

from .conftest import (
    make_document,
    make_equation,
    make_footnote,
    make_metadata,
    make_page,
    make_paragraph,
    make_processing_metadata,
    make_provenance,
    make_reference,
    make_section,
    make_statistics,
    make_table,
)


def _round_trip_dict(model):
    cls = type(model)
    dumped = model.model_dump()
    rebuilt = cls.model_validate(dumped)
    assert rebuilt == model
    return dumped


def _round_trip_json(model):
    cls = type(model)
    dumped_json = model.model_dump_json()
    rebuilt = cls.model_validate_json(dumped_json)
    assert rebuilt == model
    return dumped_json


class TestRoundTripDictAndJson:
    def test_paragraph_round_trips(self):
        p = make_paragraph()
        _round_trip_dict(p)
        _round_trip_json(p)

    def test_reference_round_trips(self):
        ref = make_reference()
        _round_trip_dict(ref)
        _round_trip_json(ref)

    def test_table_round_trips(self):
        t = make_table()
        _round_trip_dict(t)
        _round_trip_json(t)

    def test_equation_round_trips(self):
        eq = make_equation()
        _round_trip_dict(eq)
        _round_trip_json(eq)

    def test_footnote_round_trips(self):
        fn = make_footnote()
        _round_trip_dict(fn)
        _round_trip_json(fn)

    def test_section_with_reference_child_round_trips(self):
        # Specifically exercises the v1.1-corrected union through a full
        # JSON round trip, not just direct Python construction.
        section = make_section(
            heading_text="References",
            children=[make_reference(), make_reference("/page/9/ListItem/1")],
        )
        dumped = _round_trip_dict(section)
        assert dumped["children"][0]["kind"] == "reference"
        _round_trip_json(section)

    def test_page_round_trips(self):
        page = make_page(children=[make_paragraph(), make_table()])
        _round_trip_dict(page)
        _round_trip_json(page)

    def test_statistics_round_trips(self):
        stats = make_statistics()
        _round_trip_dict(stats)
        _round_trip_json(stats)

    def test_metadata_round_trips(self):
        meta = make_metadata()
        _round_trip_dict(meta)
        _round_trip_json(meta)

    def test_processing_metadata_round_trips_with_utc_datetime(self):
        pm = make_processing_metadata()
        dumped_json = _round_trip_json(pm)
        assert "2026-06-17" in dumped_json

    def test_document_round_trips(self):
        doc = make_document()
        _round_trip_dict(doc)
        _round_trip_json(doc)

    def test_document_with_full_tree_round_trips(self):
        doc = make_document(
            pages=[
                make_page(
                    0,
                    children=[
                        make_section(
                            "/page/0/SectionHeader/0",
                            heading_text="Methods",
                            children=[make_paragraph(), make_table()],
                        ),
                        make_section(
                            "/page/0/SectionHeader/1",
                            heading_text="References",
                            children=[make_reference()],
                        ),
                    ],
                )
            ]
        )
        _round_trip_dict(doc)
        _round_trip_json(doc)


class TestFieldOrderingDeterminism:
    def test_dump_json_field_order_matches_declaration_order(self):
        p = make_paragraph()
        dumped = p.model_dump_json()
        # Declared order in Paragraph: kind, id, text, provenance.
        assert dumped.index('"kind"') < dumped.index('"id"') < dumped.index(
            '"text"'
        ) < dumped.index('"provenance"')

    def test_repeated_dumps_are_byte_identical(self):
        p = make_paragraph()
        assert p.model_dump_json() == p.model_dump_json()


class TestBytesFieldSerialization:
    def test_figure_image_data_serializes_as_base64_string(self):
        raw_bytes = b"\x89PNG\r\n\x1a\nfake-bytes"
        fig = Figure(
            id=make_paragraph().id,  # any well-formed id is fine here
            provenance=make_provenance("/page/7/Figure/9"),
            image_data=raw_bytes,
        )
        dumped_json = fig.model_dump_json()
        # Pydantic v2 base64-encodes bytes fields in JSON mode by default.
        rebuilt = Figure.model_validate_json(dumped_json)
        assert rebuilt.image_data == raw_bytes

    def test_figure_with_none_image_data_round_trips(self):
        fig = Figure(
            id=make_paragraph().id,
            provenance=make_provenance("/page/7/Figure/10"),
        )
        rebuilt = Figure.model_validate_json(fig.model_dump_json())
        assert rebuilt.image_data is None