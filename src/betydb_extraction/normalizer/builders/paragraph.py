"""ParagraphBuilder — mutable accumulator for Schema v1.1 Paragraph."""
from __future__ import annotations

from dataclasses import dataclass, field

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class ParagraphBuilder:
    # Schema v1.1 discriminated-union literal — set at Stage 3 construction.
    kind: str | None = None
    text: str | None = None
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    # Stage 9 only — not present in Schema v1.1 model.
    canonical_path: str | None = None
    # Stage 10 only — final frozen id.
    