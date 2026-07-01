"""
Stage 1.5: Wrapper Unwrapping.
"""
from __future__ import annotations

from typing import Any

from betydb_extraction.normalizer.builders.base import UnwrappedBlock, WrapperContext

# The three Marker block types that Stage 1.5 unwraps.
_WRAPPER_BLOCK_TYPES: frozenset[str] = frozenset(
    {"TableGroup", "FigureGroup", "ListGroup"}
)


def unwrap_page(page_block_children: list[Any]) -> list[UnwrappedBlock]:
    result: list[UnwrappedBlock] = []

    for block in page_block_children:
        block_type: str = block.block_type

        if block_type in _WRAPPER_BLOCK_TYPES:
            # Unwrap exactly one level: each child gets the wrapper's context.
            ctx = WrapperContext(wrapper_type=block_type, block_id=block.id)
            for child in block.children:
                # Inner wrappers are NOT recursively expanded — they land here
                # tagged with the outer wrapper's ctx and are treated as
                # ordinary blocks by Stage 2.
                result.append(UnwrappedBlock(block=child, wrapper_context=ctx))
        else:
            # Direct page child — no wrapper context.
            result.append(UnwrappedBlock(block=block, wrapper_context=None))

    return result