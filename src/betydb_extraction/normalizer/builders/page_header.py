"""PageHeaderBuilder — mutable accumulator for Schema v1.1 PageHeader."""
from __future__ import annotations

from dataclasses import dataclass, field

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class PageHeaderBuilder:
    kind: str | None = None
    raw_text: str | None = None
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    canonical_path: str | None = None
    