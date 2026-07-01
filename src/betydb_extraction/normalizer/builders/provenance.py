"""
ProvenanceBuilder — mutable accumulator for StructuralProvenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProvenanceBuilder:
    marker_block_ids: list[str] = field(default_factory=list)
    page_number: int | None = None
    # BoundingBox and Polygon are frozen leaf value types from the Schema;
    # they are stored here directly once constructed (Stage 3 / Stage 4).
    bbox: Any | None = None               # BoundingBox | None
    contributing_bboxes: list[Any] | None = None  # list[BoundingBox] | None
    polygon: Any | None = None            # Polygon | None
    section_path: list[str] = field(default_factory=list)
    reading_order_index: int | None = None