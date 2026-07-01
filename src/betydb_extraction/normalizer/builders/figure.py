"""FigureBuilder — mutable accumulator for Schema v1.1 Figure."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class FigureBuilder:
    kind: str | None = None
    image_data: Any | None = None          # bytes | None; from source block images
    caption: Any | None = None             # CaptionBuilder | None; Stage 4
    footnote_ids: list[str] = field(default_factory=list)  # Stage 6
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    canonical_path: str | None = None
