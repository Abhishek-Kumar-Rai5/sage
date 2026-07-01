from __future__ import annotations

import json
from pathlib import Path

import pytest

from betydb_extraction.marker_adapter.raw_model import (
    MarkerBBox,
    MarkerBlock,
    MarkerDocument,
    MarkerPolygonPoint,
)

REAL_FIXTURE_PATH = Path(
    "/mnt/user-data/uploads/1781681908897_Nutrient-cycling.json"
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _minimal_leaf_block(
    block_id: str = "/page/0/Text/0",
    block_type: str = "Text",
    html: str = "<p>hello</p>",
) -> dict:
    """A minimal, valid leaf block dict matching Marker's observed envelope."""
    return {
        "id": block_id,
        "block_type": block_type,
        "html": html,
        "polygon": [[0.0, 0.0], [100.0, 0.0], [100.0, 10.0], [0.0, 10.0]],
        "bbox": [0.0, 0.0, 100.0, 10.0],
        "children": None,
        "section_hierarchy": {},
        "images": {},
    }


def _minimal_container_block(
    block_id: str,
    block_type: str,
    children: list[dict],
) -> dict:
    """A minimal, valid container block dict wrapping the given children."""
    return {
        "id": block_id,
        "block_type": block_type,
        "html": "".join(f"<content-ref src='{c['id']}'></content-ref>" for c in children),
        "polygon": [[0.0, 0.0], [200.0, 0.0], [200.0, 200.0], [0.0, 200.0]],
        "bbox": [0.0, 0.0, 200.0, 200.0],
        "children": children,
        "section_hierarchy": {},
        "images": {},
    }


@pytest.fixture(scope="module")
def real_marker_json() -> dict:
    if not REAL_FIXTURE_PATH.exists():
        pytest.skip(f"Real Marker fixture not present at {REAL_FIXTURE_PATH}")
    with open(REAL_FIXTURE_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Construction / validation -- synthetic inputs
# ---------------------------------------------------------------------------


class TestMarkerPolygonPoint:
    def test_construct_from_pair(self):
        point = MarkerPolygonPoint.from_pair([12.5, 34.0])
        assert point.x == 12.5
        assert point.y == 34.0

    def test_to_pair_round_trip(self):
        point = MarkerPolygonPoint(x=1.0, y=2.0)
        assert point.to_pair() == [1.0, 2.0]

    def test_is_frozen(self):
        point = MarkerPolygonPoint(x=1.0, y=2.0)
        with pytest.raises(Exception):
            point.x = 5.0  # type: ignore[misc]

    def test_rejects_extra_fields(self):
        with pytest.raises(Exception):
            MarkerPolygonPoint(x=1.0, y=2.0, z=3.0)  # type: ignore[call-arg]


class TestMarkerBBox:
    def test_construct_from_list(self):
        bbox = MarkerBBox.from_list([0.0, 0.0, 10.0, 20.0])
        assert (bbox.x0, bbox.y0, bbox.x1, bbox.y1) == (0.0, 0.0, 10.0, 20.0)

    def test_to_list_round_trip(self):
        bbox = MarkerBBox(x0=0.0, y0=1.0, x1=2.0, y1=3.0)
        assert bbox.to_list() == [0.0, 1.0, 2.0, 3.0]

    def test_is_frozen(self):
        bbox = MarkerBBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
        with pytest.raises(Exception):
            bbox.x0 = 99.0  # type: ignore[misc]


class TestMarkerBlockConstruction:
    def test_construct_minimal_leaf(self):
        block = MarkerBlock.model_validate(_minimal_leaf_block())
        assert block.block_type == "Text"
        assert block.is_leaf()
        assert block.children is None

    def test_construct_container_with_children(self):
        leaf = _minimal_leaf_block()
        container = _minimal_container_block(
            "/page/0/TableGroup/1", "TableGroup", [leaf]
        )
        block = MarkerBlock.model_validate(container)
        assert not block.is_leaf()
        assert len(block.children) == 1
        assert block.children[0].block_type == "Text"

    def test_polygon_coerced_from_raw_pairs(self):
        block = MarkerBlock.model_validate(_minimal_leaf_block())
        assert isinstance(block.polygon[0], MarkerPolygonPoint)
        assert block.polygon[0].x == 0.0
        assert block.polygon[0].y == 0.0

    def test_bbox_coerced_from_raw_list(self):
        block = MarkerBlock.model_validate(_minimal_leaf_block())
        assert isinstance(block.bbox, MarkerBBox)
        assert block.bbox.x1 == 100.0

    def test_root_document_block_with_no_id_or_geometry(self):
        data = {
            "children": [_minimal_leaf_block()],
            "block_type": "Document",
        }
        block = MarkerBlock.model_validate(data)
        assert block.id is None
        assert block.bbox is None
        assert block.polygon is None
        assert block.section_hierarchy == {}
        assert len(block.children) == 1

    def test_unknown_block_type_parses_successfully(self):
        data = _minimal_leaf_block(block_type="SomeFutureBlockType")
        block = MarkerBlock.model_validate(data)
        assert block.block_type == "SomeFutureBlockType"

    def test_unknown_extra_field_is_preserved_not_dropped(self):
        data = _minimal_leaf_block()
        data["confidence_score"] = 0.987  # hypothetical future Marker field
        block = MarkerBlock.model_validate(data)
        dumped = block.model_dump(mode="json")
        assert dumped["confidence_score"] == 0.987

    def test_missing_required_block_type_raises(self):
        data = _minimal_leaf_block()
        del data["block_type"]
        with pytest.raises(Exception):
            MarkerBlock.model_validate(data)

    def test_is_frozen_immutable(self):
        block = MarkerBlock.model_validate(_minimal_leaf_block())
        with pytest.raises(Exception):
            block.html = "<p>mutated</p>"  # type: ignore[misc]

    def test_nested_children_are_also_frozen(self):
        leaf = _minimal_leaf_block()
        container = _minimal_container_block(
            "/page/0/TableGroup/1", "TableGroup", [leaf]
        )
        block = MarkerBlock.model_validate(container)
        with pytest.raises(Exception):
            block.children[0].html = "<p>mutated</p>"  # type: ignore[misc]

    def test_iter_descendants_depth_first_order(self):
        grandchild = _minimal_leaf_block("/page/0/Text/2", "Text")
        child_container = _minimal_container_block(
            "/page/0/Caption/1", "Caption", [grandchild]
        )
        root_container = _minimal_container_block(
            "/page/0/TableGroup/0", "TableGroup", [child_container]
        )
        block = MarkerBlock.model_validate(root_container)
        descendants = block.iter_descendants()
        assert [d.id for d in descendants] == [
            "/page/0/Caption/1",
            "/page/0/Text/2",
        ]

    def test_iter_descendants_empty_for_leaf(self):
        block = MarkerBlock.model_validate(_minimal_leaf_block())
        assert block.iter_descendants() == []

    def test_images_dict_preserved(self):
        data = _minimal_leaf_block(block_type="Picture")
        data["images"] = {"/page/0/Picture/0": "base64fakepayload=="}
        block = MarkerBlock.model_validate(data)
        assert block.images == {"/page/0/Picture/0": "base64fakepayload=="}

    def test_children_none_vs_empty_list_distinction_preserved(self):
        leaf_data = _minimal_leaf_block()
        leaf_data["children"] = None
        leaf_block = MarkerBlock.model_validate(leaf_data)
        assert leaf_block.children is None

        empty_list_data = _minimal_leaf_block()
        empty_list_data["children"] = []
        empty_list_block = MarkerBlock.model_validate(empty_list_data)
        assert empty_list_block.children == []
        # These are deliberately NOT equal in meaning -- is_leaf() should
        # only be True for the None case.
        assert leaf_block.is_leaf() is True
        assert empty_list_block.is_leaf() is False


class TestMarkerDocument:
    def test_wraps_root_block(self):
        leaf = _minimal_leaf_block()
        root_data = _minimal_container_block("doc-root", "Document", [leaf])
        root_block = MarkerBlock.model_validate(root_data)
        doc = MarkerDocument(root=root_block)
        assert doc.root.block_type == "Document"

    def test_pages_property_returns_root_children(self):
        page_block = _minimal_container_block("/page/0/Page/0", "Page", [])
        root_data = _minimal_container_block("doc-root", "Document", [page_block])
        root_block = MarkerBlock.model_validate(root_data)
        doc = MarkerDocument(root=root_block)
        assert len(doc.pages) == 1
        assert doc.pages[0].block_type == "Page"

    def test_pages_property_empty_when_no_children(self):
        root_block = MarkerBlock.model_validate(
            {"children": None, "block_type": "Document"}
        )
        doc = MarkerDocument(root=root_block)
        assert doc.pages == []

    def test_source_path_optional_and_retained(self):
        root_block = MarkerBlock.model_validate(
            {"children": None, "block_type": "Document"}
        )
        doc = MarkerDocument(root=root_block, source_marker_json_path="/tmp/x.json")
        assert doc.source_marker_json_path == "/tmp/x.json"

    def test_is_frozen(self):
        root_block = MarkerBlock.model_validate(
            {"children": None, "block_type": "Document"}
        )
        doc = MarkerDocument(root=root_block)
        with pytest.raises(Exception):
            doc.source_marker_json_path = "/tmp/other.json"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 2. Construction / validation -- real Marker output (ground truth)
# ---------------------------------------------------------------------------


class TestRealMarkerDocument:
    def test_parses_without_error(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        assert block.block_type == "Document"

    def test_root_has_no_id(self, real_marker_json):
        """Confirmed empirical fact: the real root block has no `id` field."""
        block = MarkerBlock.model_validate(real_marker_json)
        assert block.id is None

    def test_page_count_matches_known_value(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        doc = MarkerDocument(root=block)
        assert len(doc.pages) == 17

    def test_total_descendant_count_matches_known_census(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        assert len(block.iter_descendants()) == 1085

    def test_table_group_pattern_caption_then_table(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        table_groups = [
            d for d in block.iter_descendants() if d.block_type == "TableGroup"
        ]
        assert len(table_groups) == 3
        for tg in table_groups:
            assert len(tg.children) == 2
            assert tg.children[0].block_type == "Caption"
            assert tg.children[1].block_type == "Table"

    def test_figure_group_pattern_figure_then_caption(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        figure_groups = [
            d for d in block.iter_descendants() if d.block_type == "FigureGroup"
        ]
        assert len(figure_groups) == 1
        fg = figure_groups[0]
        assert len(fg.children) == 2
        assert fg.children[0].block_type == "Figure"
        assert fg.children[1].block_type == "Caption"

    def test_page_7_has_bare_tables_and_flat_footnotes(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        doc = MarkerDocument(root=block)
        page7 = doc.pages[7]
        child_types = [c.block_type for c in page7.children]
        assert child_types.count("Table") == 2
        assert child_types.count("Footnote") == 3
        assert "TableGroup" not in child_types

    def test_table_block_has_both_html_and_table_cell_children(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        tables = [d for d in block.iter_descendants() if d.block_type == "Table"]
        assert len(tables) == 7
        for table in tables:
            assert "<table>" in table.html
            assert table.children is not None
            assert all(c.block_type == "TableCell" for c in table.children)

    def test_picture_blocks_carry_image_payloads(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        pictures = [d for d in block.iter_descendants() if d.block_type == "Picture"]
        assert len(pictures) == 2
        for pic in pictures:
            assert pic.images
            assert len(next(iter(pic.images.values()))) > 100  # real base64 payload


# ---------------------------------------------------------------------------
# 3. Round-trip serialization losslessness
# ---------------------------------------------------------------------------


class TestRoundTripSerialization:
    def test_synthetic_block_round_trip_via_dict(self):
        leaf = _minimal_leaf_block()
        container = _minimal_container_block(
            "/page/0/TableGroup/0", "TableGroup", [leaf]
        )
        block = MarkerBlock.model_validate(container)
        dumped = block.model_dump(mode="json")
        reparsed = MarkerBlock.model_validate(dumped)
        assert reparsed.model_dump(mode="json") == dumped

    def test_synthetic_block_round_trip_via_json_string(self):
        block = MarkerBlock.model_validate(_minimal_leaf_block())
        json_str = block.model_dump_json()
        reparsed = MarkerBlock.model_validate_json(json_str)
        assert reparsed.model_dump(mode="json") == block.model_dump(mode="json")

    def test_real_document_round_trip_via_dict_is_lossless(self, real_marker_json):
        block = MarkerBlock.model_validate(real_marker_json)
        dumped = block.model_dump(mode="json")
        reparsed = MarkerBlock.model_validate(dumped)
        assert reparsed.model_dump(mode="json") == dumped

    def test_real_document_round_trip_preserves_descendant_ids_in_order(
        self, real_marker_json
    ):
        block = MarkerBlock.model_validate(real_marker_json)
        dumped = block.model_dump(mode="json")
        reparsed = MarkerBlock.model_validate(dumped)
        orig_ids = [d.id for d in block.iter_descendants()]
        reparsed_ids = [d.id for d in reparsed.iter_descendants()]
        assert orig_ids == reparsed_ids

    def test_real_document_round_trip_via_json_string_is_lossless(
        self, real_marker_json
    ):
        block = MarkerBlock.model_validate(real_marker_json)
        json_str = block.model_dump_json()
        reparsed = MarkerBlock.model_validate_json(json_str)
        assert reparsed.model_dump(mode="json") == block.model_dump(mode="json")

    def test_serialization_is_deterministic_across_repeated_dumps(
        self, real_marker_json
    ):

        block = MarkerBlock.model_validate(real_marker_json)
        dump1 = block.model_dump_json()
        dump2 = block.model_dump_json()
        assert dump1 == dump2

    def test_unknown_extra_field_survives_full_round_trip(self):
        data = _minimal_leaf_block()
        data["some_future_field"] = {"nested": [1, 2, 3]}
        block = MarkerBlock.model_validate(data)
        json_str = block.model_dump_json()
        reparsed = MarkerBlock.model_validate_json(json_str)
        assert reparsed.model_dump(mode="json")["some_future_field"] == {
            "nested": [1, 2, 3]
        }
