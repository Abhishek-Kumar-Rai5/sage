"""Tests for betydb_extraction.document.provenance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from betydb_extraction.document.provenance import (
    BoundingBox,
    Polygon,
    StructuralProvenance,
)


class TestBoundingBox:
    def test_valid_box_constructs(self):
        box = BoundingBox(x0=0, y0=0, x1=10, y1=20)
        assert (box.x0, box.y0, box.x1, box.y1) == (0, 0, 10, 20)

    def test_zero_area_box_is_allowed(self):
        # Spec 20 only requires x1 >= x0 and y1 >= y0, not strict >.
        box = BoundingBox(x0=5, y0=5, x1=5, y1=5)
        assert box.x1 == box.x0

    def test_inverted_x_axis_rejected(self):
        with pytest.raises(ValidationError):
            BoundingBox(x0=10, y0=0, x1=0, y1=10)

    def test_inverted_y_axis_rejected(self):
        with pytest.raises(ValidationError):
            BoundingBox(x0=0, y0=10, x1=10, y1=0)

    def test_is_frozen(self):
        box = BoundingBox(x0=0, y0=0, x1=1, y1=1)
        with pytest.raises(ValidationError):
            box.x0 = 5

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            BoundingBox(x0=0, y0=0, x1=1, y1=1, z0=0)


class TestPolygon:
    def test_valid_polygon_constructs(self):
        poly = Polygon(points=((0, 0), (10, 0), (10, 10), (0, 10)))
        assert len(poly.points) == 4

    def test_wrong_point_count_rejected(self):
        with pytest.raises(ValidationError):
            Polygon(points=((0, 0), (10, 0), (10, 10)))

    def test_is_frozen(self):
        poly = Polygon(points=((0, 0), (10, 0), (10, 10), (0, 10)))
        with pytest.raises(ValidationError):
            poly.points = ((0, 0), (1, 0), (1, 1), (0, 1))


class TestStructuralProvenance:
    def test_minimal_valid_construction(self):
        prov = StructuralProvenance(
            marker_block_ids=["/page/0/Text/0"],
            page_number=0,
            reading_order_index=0,
        )
        assert prov.bbox is None
        assert prov.contributing_bboxes is None
        assert prov.section_path == []

    def test_empty_marker_block_ids_rejected(self):
        with pytest.raises(ValidationError):
            StructuralProvenance(
                marker_block_ids=[],
                page_number=0,
                reading_order_index=0,
            )

    def test_negative_reading_order_index_rejected(self):
        with pytest.raises(ValidationError):
            StructuralProvenance(
                marker_block_ids=["/page/0/Text/0"],
                page_number=0,
                reading_order_index=-1,
            )

    def test_bbox_and_contributing_bboxes_mutually_exclusive(self):
        box = BoundingBox(x0=0, y0=0, x1=1, y1=1)
        with pytest.raises(ValidationError):
            StructuralProvenance(
                marker_block_ids=["/page/0/Text/0"],
                page_number=0,
                reading_order_index=0,
                bbox=box,
                contributing_bboxes=[box],
            )

    def test_bbox_alone_is_valid(self):
        box = BoundingBox(x0=0, y0=0, x1=1, y1=1)
        prov = StructuralProvenance(
            marker_block_ids=["/page/0/Text/0"],
            page_number=0,
            reading_order_index=0,
            bbox=box,
        )
        assert prov.bbox == box

    def test_contributing_bboxes_alone_is_valid(self):
        box = BoundingBox(x0=0, y0=0, x1=1, y1=1)
        prov = StructuralProvenance(
            marker_block_ids=["/page/0/SectionHeader/0", "/page/0/Text/1"],
            page_number=0,
            reading_order_index=0,
            contributing_bboxes=[box, box],
        )
        assert len(prov.contributing_bboxes) == 2

    def test_neither_bbox_field_is_valid(self):
        # No recoverable geometry is a legitimate outcome (Section 3.3).
        prov = StructuralProvenance(
            marker_block_ids=["/page/0/Text/0"],
            page_number=0,
            reading_order_index=0,
        )
        assert prov.bbox is None and prov.contributing_bboxes is None

    def test_section_path_preserves_order(self):
        prov = StructuralProvenance(
            marker_block_ids=["/page/7/TableCell/3"],
            page_number=7,
            reading_order_index=42,
            section_path=[
                "/page/1/SectionHeader/1",
                "/page/7/SectionHeader/0",
            ],
        )
        assert prov.section_path == [
            "/page/1/SectionHeader/1",
            "/page/7/SectionHeader/0",
        ]

    def test_is_frozen(self):
        prov = StructuralProvenance(
            marker_block_ids=["/page/0/Text/0"],
            page_number=0,
            reading_order_index=0,
        )
        with pytest.raises(ValidationError):
            prov.page_number = 1