"""
Stage 7: Section Tree Assembly.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.section import SectionBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.base import Disposition

logger = logging.getLogger(__name__)


def _numeric_sort_key(depth_key: str) -> int:
    try:
        return int(depth_key)
    except ValueError:
        return 10_000


def _get_section_hierarchy(marker_block: Any) -> dict[str, str]:
    raw = getattr(marker_block, "section_hierarchy", None)
    if raw is None:
        return {}
    return dict(raw)  # defensive copy


def _sorted_hierarchy_entries(
    section_hierarchy: dict[str, str],
) -> list[tuple[int, str]]:
    return sorted(
        ((int(k), v) for k, v in section_hierarchy.items() if k.isdigit()),
        key=lambda pair: pair[0],
    )

def assemble_section_tree(
    page_builders: list[PageBuilder],
    classified_pages: list[list[Any]],
) -> None:
    """
    Stage 7 entry point.
    """
    #Step 1

    # heading_registry[marker_block_id] = SectionBuilder
    heading_registry: dict[str, SectionBuilder] = {}

    # heading_page_index[marker_block_id] = page_index
    heading_page_index: dict[str, int] = {}

    # heading_seq_pos[marker_block_id] = position in that page's classified seq
    heading_seq_pos: dict[str, int] = {}

    for page_index, classified_blocks in enumerate(classified_pages):
        for seq_pos, cb in enumerate(classified_blocks):
            if cb.disposition != Disposition.GENUINE_SECTION_HEADER:
                continue

            block = cb.unwrapped.block
            heading_id: str = block.id
            heading_html: str = getattr(block, "html", "") or ""

            # Build provenance for the SectionBuilder heading.
            from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
            prov = ProvenanceBuilder(
                marker_block_ids=[heading_id],
                page_number=page_index,
                bbox=getattr(block, "bbox", None),
                polygon=getattr(block, "polygon", None),
            )

            sb = SectionBuilder(
                heading_text=heading_html,
                heading_marker_block_id=heading_id,
                provenance=prov,
                children=[],
            )

            heading_registry[heading_id] = sb
            heading_page_index[heading_id] = page_index
            heading_seq_pos[heading_id] = seq_pos

            logger.debug(
                "stage7 step1 registered heading marker_block_id=%s page=%d seq_pos=%d",
                heading_id,
                page_index,
                seq_pos,
            )

    if not heading_registry:
        logger.debug("stage7 no GENUINE_SECTION_HEADER blocks found; skipping tree assembly")
        return

#Step 2
    heading_depth: dict[str, int] = {}

    heading_parent_id: dict[str, str] = {}

    heading_has_content: set[str] = set()

    for page_index, classified_blocks in enumerate(classified_pages):
        for cb in classified_blocks:
            if cb.disposition == Disposition.GENUINE_SECTION_HEADER:
                continue

            block = cb.unwrapped.block
            sh: dict[str, str] = _get_section_hierarchy(block)
            if not sh:
                continue

            sorted_entries = _sorted_hierarchy_entries(sh)
            for list_pos, (depth_int, ref_heading_id) in enumerate(sorted_entries):
                if ref_heading_id not in heading_registry:

                    continue

                heading_has_content.add(ref_heading_id)

                if ref_heading_id not in heading_depth:
                    heading_depth[ref_heading_id] = depth_int

                if depth_int > 0 and ref_heading_id not in heading_parent_id:
                    if list_pos > 0:
                        parent_heading_id = sorted_entries[list_pos - 1][1]
                        if parent_heading_id in heading_registry:
                            heading_parent_id[ref_heading_id] = parent_heading_id


    omitted_heading_ids: set[str] = set()
    for heading_id, sb in heading_registry.items():
        if heading_id not in heading_has_content:
            omitted_heading_ids.add(heading_id)
            logger.debug(
                "stage7 step2 omitting heading marker_block_id=%s "
                "(no governed content found)",
                heading_id,
            )
            continue

        sb.depth = heading_depth.get(heading_id, 0)
        sb.kind = "section"  # Schema v1.1 discriminated-union literal

        parent_id = heading_parent_id.get(heading_id)
        if parent_id and parent_id not in omitted_heading_ids:
            sb.parent_section_builder = heading_registry.get(parent_id)
        else:
            sb.parent_section_builder = None

        logger.debug(
            "stage7 step2 heading marker_block_id=%s depth=%d parent=%s",
            heading_id,
            sb.depth,
            parent_id,
        )
    

    non_omitted = [
        (heading_id, sb)
        for heading_id, sb in heading_registry.items()
        if heading_id not in omitted_heading_ids
    ]
    for heading_id, sb in sorted(non_omitted, key=lambda pair: pair[1].depth or 0):
        parent = sb.parent_section_builder
        if parent is not None:
            sb.provenance.section_path = list(parent.provenance.section_path) + [
                parent.heading_marker_block_id
            ]
        else:
            sb.provenance.section_path = []

    logger.debug(
        "stage7 step2 complete: section_path set on %d non-omitted SectionBuilders",
        len(non_omitted),
    )

# Step 3
    mbid_to_builder: dict[str, Any] = {}
    for pb in page_builders:
        for builder in pb.children:
            if isinstance(builder, SectionBuilder):
                continue
            mids = getattr(getattr(builder, "provenance", None), "marker_block_ids", [])
            if mids:
                mbid_to_builder[mids[0]] = builder

    # Now resolve section_path for every leaf builder.
    # builder_governing_section[builder_python_id] = innermost SectionBuilder | None
    builder_governing_section: dict[int, SectionBuilder | None] = {}

    for page_index, classified_blocks in enumerate(classified_pages):
        for cb in classified_blocks:
            if cb.disposition == Disposition.GENUINE_SECTION_HEADER:
                continue

            block = cb.unwrapped.block
            block_id: str = getattr(block, "id", None)
            if block_id is None:
                continue

            builder = mbid_to_builder.get(block_id)
            if builder is None:
                continue

            sh: dict[str, str] = _get_section_hierarchy(block)
            if not sh:
                builder.provenance.section_path = []
                builder_governing_section[id(builder)] = None
                continue

            sorted_entries = _sorted_hierarchy_entries(sh)

            # Filter to heading ids actually present in our registry and not omitted.
            resolved_ids: list[str] = []
            innermost_sb: SectionBuilder | None = None
            for _depth, heading_id in sorted_entries:
                if heading_id in heading_registry and heading_id not in omitted_heading_ids:
                    resolved_ids.append(heading_id)
                    innermost_sb = heading_registry[heading_id]

            builder.provenance.section_path = resolved_ids
            builder_governing_section[id(builder)] = innermost_sb

    logger.debug("stage7 step3 complete: section_path populated on all leaf builders")

#step 4
    for pb in page_builders:
        pb.children = []

    builder_page_index: dict[int, int] = {}
    for page_index, classified_blocks in enumerate(classified_pages):
        for cb in classified_blocks:
            if cb.disposition == Disposition.GENUINE_SECTION_HEADER:
                continue
            block = cb.unwrapped.block
            block_id = getattr(block, "id", None)
            if block_id is None:
                continue
            builder = mbid_to_builder.get(block_id)
            if builder is None:
                continue
            builder_page_index[id(builder)] = page_index

    # Place each leaf builder into its governing SectionBuilder or its page.
    for py_id, governing_sb in builder_governing_section.items():
        pass  # handled in the loop below

    # Rebuild: python id → builder object (needed to retrieve from builder_governing_section)
    pyid_to_builder: dict[int, Any] = {
        id(b): b for b in mbid_to_builder.values()
    }

    for py_id, governing_sb in builder_governing_section.items():
        builder = pyid_to_builder.get(py_id)
        if builder is None:
            continue  # safety guard
        is_page_furniture = type(builder).__name__ in (
            "PageHeaderBuilder", "PageFooterBuilder"
        )

        if governing_sb is not None and not is_page_furniture:
            governing_sb.children.append(builder)
        else:
            if is_page_furniture:
                builder.provenance.section_path = []
            page_idx = builder_page_index.get(py_id, 0)
            page_builders[page_idx].children.append(builder)

    logger.debug("stage7 step4 complete: leaf builders placed into parents")

    #Step 5 

    for heading_id, sb in heading_registry.items():
        if heading_id in omitted_heading_ids:
            continue

        if sb.parent_section_builder is not None:
            sb.parent_section_builder.children.append(sb)
        else:
            # Top-level section (depth 0): attach to the PageBuilder of the
            # page where the heading block appears.
            page_idx = heading_page_index.get(heading_id, 0)
            page_builders[page_idx].children.append(sb)

    logger.debug("stage7 step5 complete: SectionBuilders nested")

    # ── Step 6 
    mbid_to_seq: dict[str, tuple[int, int]] = {}
    for page_index, classified_blocks in enumerate(classified_pages):
        for seq_pos, cb in enumerate(classified_blocks):
            block_id = getattr(cb.unwrapped.block, "id", None)
            if block_id is not None:
                mbid_to_seq[block_id] = (page_index, seq_pos)

    def _sort_key(item: Any) -> tuple[int, int]:
        if isinstance(item, SectionBuilder):
            hid = item.heading_marker_block_id
            return mbid_to_seq.get(hid, (0, 0))
        else:
            # Leaf builder: use its first Marker block id.
            mids = getattr(getattr(item, "provenance", None), "marker_block_ids", [])
            if mids:
                return mbid_to_seq.get(mids[0], (0, 0))
            return (0, 0)

    def _sort_children(children: list[Any]) -> None:
        children.sort(key=_sort_key)

    # Sort each PageBuilder.children.
    for pb in page_builders:
        _sort_children(pb.children)

    # Sort each SectionBuilder.children (all non-omitted sections).
    for heading_id, sb in heading_registry.items():
        if heading_id in omitted_heading_ids:
            continue
        _sort_children(sb.children)

    logger.debug("stage7 step6 complete: all children lists sorted by classified-sequence position")
    logger.debug(
        "stage7 complete: %d sections registered, %d omitted",
        len(heading_registry) - len(omitted_heading_ids),
        len(omitted_heading_ids),
    )