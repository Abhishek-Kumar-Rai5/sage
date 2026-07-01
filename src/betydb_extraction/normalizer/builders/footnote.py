"""FootnoteBuilder — mutable accumulator for Schema v1.1 Footnote."""
from __future__ import annotations

from dataclasses import dataclass, field

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class FootnoteBuilder:
    kind: str | None = None
    raw_text: str | None = None
    # Set by Stage 6; left None if no candidate table/figure found.
    attached_object_id: str | None = None
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    canonical_path: str | None = None
    