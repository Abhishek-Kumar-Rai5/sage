"""CaptionBuilder — mutable accumulator for Schema v1.1 Caption."""
from __future__ import annotations

from dataclasses import dataclass, field

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class CaptionBuilder:
    # kind is set at Stage 4 (not Stage 3), per spec §4.1 kind field rule.
    kind: str | None = None
    label: str | None = None
    text: str | None = None
    trailing_notes: str | None = None
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    canonical_path: str | None = None