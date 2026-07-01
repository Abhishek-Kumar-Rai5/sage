"""
Stage 1: Page Builder Construction.
"""
from __future__ import annotations

from typing import Any

from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


def build_page_shells(
    page_blocks: list[Any],          # list[MarkerBlock] — top-level page nodes
    front_matter_flags: dict[int, bool],  # Stage 0 output: page_index → bool
) -> list[PageBuilder]:
    shells: list[PageBuilder] = []

    for page_index, page_block in enumerate(page_blocks):
        # Spec: bbox from page_block.bbox if present, else None.
        bbox = getattr(page_block, "bbox", None)

        provenance = ProvenanceBuilder(
            marker_block_ids=[page_block.id],
            page_number=page_index,
            bbox=bbox,
            # polygon: MarkerDocument root page blocks carry no polygon
            # (not confirmed empirically — left None per conservative rule).
            polygon=None,
        )

        shell = PageBuilder(
            page_number=page_index,
            is_front_matter=front_matter_flags.get(page_index, False),
            provenance=provenance,
            # children: empty — Stage 7 populates.
            children=[],
        )

        shells.append(shell)

    return shells