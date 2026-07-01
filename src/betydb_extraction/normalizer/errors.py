"""
Normalizer exception hierarchy.
"""
from __future__ import annotations


class NormalizerError(Exception):
      """Base class for all normalizer exceptions."""

class UnrecognizedBlockTypeError(NormalizerError):
    def __init__(self, block_type: str, marker_block_id: str, page_index: int) -> None:
        self.block_type = block_type
        self.marker_block_id = marker_block_id
        self.page_index = page_index
        super().__init__(
            f"Unrecognized block_type={block_type!r} "
            f"(marker_block_id={marker_block_id!r}, page_index={page_index})"
        )


class WholeTreeInvariantViolationError(NormalizerError):
    def __init__(
        self,
        invariant_number: int,
        description: str,
        offending_object_ids: list[str] | None = None,
    ) -> None:
        self.invariant_number = invariant_number
        self.description = description
        self.offending_object_ids: list[str] = offending_object_ids or []
        super().__init__(
            f"Invariant {invariant_number} violated: {description} "
            f"(offending ids: {self.offending_object_ids})"
        )