"""
Stage 8: Global Reading-Order Assignment.
"""

from __future__ import annotations

import logging
from typing import Any

from betydb_extraction.normalizer.builders.page import PageBuilder
from betydb_extraction.normalizer.builders.section import SectionBuilder

logger = logging.getLogger(__name__)


def _assign_index(builder: Any, counter: list[int]) -> None:
    builder.provenance.reading_order_index = counter[0]
    counter[0] += 1


def _traverse(item: Any, counter: list[int]) -> None:
    _assign_index(item, counter)

    if isinstance(item, SectionBuilder):
        for child in item.children:
            _traverse(child, counter)
    else:
        caption = getattr(item, "caption", None)
        if caption is not None:
            _assign_index(caption, counter)


def assign_reading_order(page_builders: list[PageBuilder]) -> None:
    # Single shared counter across the entire document.
    # Wrapped in a list for mutability inside nested helper functions.
    counter: list[int] = [0]

    for page_builder in sorted(page_builders, key=lambda pb: pb.page_number or 0):
        # Assign the PageBuilder itself first (pre-order).
        _assign_index(page_builder, counter)

        # Traverse children in the order Stage 7 established.
        for child in page_builder.children:
            _traverse(child, counter)

    total_assigned = counter[0]
    logger.debug(
        "stage8 complete: reading_order_index assigned to %d builders",
        total_assigned,
    )
    