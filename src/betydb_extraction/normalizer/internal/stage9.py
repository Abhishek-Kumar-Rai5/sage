"""
Stage 9: Canonical Path Computation.
"""

from __future__ import annotations

import logging
from typing import Any

from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.section import SectionBuilder

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _class_name(obj: Any) -> str:
    return type(obj).__name__


def _first_marker_block_id(builder: Any) -> str:
    mids = getattr(getattr(builder, "provenance", None), "marker_block_ids", [])
    if not mids:
        raise ValueError(
            f"Builder {_class_name(builder)} has no marker_block_ids — "
            "cannot compute canonical_path."
        )
    return mids[0]


def _reading_order_index(builder: Any) -> int:
    roi = getattr(getattr(builder, "provenance", None), "reading_order_index", None)
    if roi is None:
        raise ValueError(
            f"Builder {_class_name(builder)} has no reading_order_index — "
            "Stage 8 must run before Stage 9."
        )
    return roi


def _set_sub_object_paths(table_builder: Any, table_path: str) -> None:
    # TableRow and TableRowCell
    for row_ordinal, row_builder in enumerate(getattr(table_builder, "rows", []) or []):
        row_path = f"{table_path}/row/{row_ordinal}"
        row_builder.canonical_path = row_path

        for cell_ordinal, cell_builder in enumerate(
            getattr(row_builder, "cells", []) or []
        ):
            cell_builder.canonical_path = f"{row_path}/cell/{cell_ordinal}"

    # Flat TableCell evidence (bare cell list)
    for tc_builder in getattr(table_builder, "cells", []) or []:
        mbid = tc_builder.marker_block_id
        if mbid is None:
            raise ValueError(
                "Stage 9: TableCellBuilder has no marker_block_id — "
                "cannot compute canonical_path."
            )
        tc_builder.canonical_path = f"{table_path}/cell_evidence/{mbid}"

    # Caption
    caption = getattr(table_builder, "caption", None)
    if caption is not None:
        caption.canonical_path = f"{table_path}/caption"
        caption.provenance.section_path = list(table_builder.provenance.section_path)


def _set_figure_sub_paths(figure_builder: Any, figure_path: str) -> None:
    caption = getattr(figure_builder, "caption", None)
    if caption is not None:
        caption.canonical_path = f"{figure_path}/caption"
        caption.provenance.section_path = list(figure_builder.provenance.section_path)


def _page_path_for(builder: Any) -> str:
    page_number = getattr(getattr(builder, "provenance", None), "page_number", None)
    if page_number is None:
        raise ValueError(
            f"Stage 9: {_class_name(builder)} has no provenance.page_number — "
            "cannot compute canonical_path."
        )
    return f"/page/{page_number}"


def _set_leaf_path(builder: Any) -> None:
    page_path = _page_path_for(builder)
    name = _class_name(builder)

    if name == "ParagraphBuilder":
        builder.canonical_path = (
            f"{page_path}/paragraph/{_reading_order_index(builder)}"
        )

    elif name == "EquationBuilder":
        builder.canonical_path = (
            f"{page_path}/equation/{_reading_order_index(builder)}"
        )

    elif name == "FootnoteBuilder":
        builder.canonical_path = (
            f"{page_path}/footnote/{_first_marker_block_id(builder)}"
        )

    elif name == "ReferenceBuilder":
        builder.canonical_path = (
            f"{page_path}/reference/{_reading_order_index(builder)}"
        )

    elif name == "PageHeaderBuilder":
        builder.canonical_path = (
            f"{page_path}/page_header/{_first_marker_block_id(builder)}"
        )

    elif name == "PageFooterBuilder":
        builder.canonical_path = (
            f"{page_path}/page_footer/{_first_marker_block_id(builder)}"
        )

    elif name == "TableBuilder":
        table_path = f"{page_path}/table/{_first_marker_block_id(builder)}"
        builder.canonical_path = table_path
        _set_sub_object_paths(builder, table_path)

    elif name == "FigureBuilder":
        figure_path = f"{page_path}/figure/{_first_marker_block_id(builder)}"
        builder.canonical_path = figure_path
        _set_figure_sub_paths(builder, figure_path)

    else:
        logger.warning(
            "stage9: unrecognised builder class %r; canonical_path not set", name
        )


def _traverse_section(section_builder: SectionBuilder) -> None:
    page_path = _page_path_for(section_builder)
    heading_id = section_builder.heading_marker_block_id or ""
    section_builder.canonical_path = f"{page_path}/section/{heading_id}"

    for child in section_builder.children:
        if isinstance(child, SectionBuilder):
            _traverse_section(child)
        else:
            _set_leaf_path(child)

def compute_canonical_paths(page_builders: list[PageBuilder]) -> None:
    for page_builder in sorted(page_builders, key=lambda pb: pb.page_number or 0):
        page_num = page_builder.page_number
        page_path = f"/page/{page_num}"
        page_builder.canonical_path = page_path

        for child in page_builder.children:
            if isinstance(child, SectionBuilder):
                _traverse_section(child)
            else:
                _set_leaf_path(child)

    logger.debug("stage9 complete: canonical_path set on all builders")