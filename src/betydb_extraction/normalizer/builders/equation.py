"""EquationBuilder — mutable accumulator for Schema v1.1 Equation."""
from __future__ import annotations

from dataclasses import dataclass, field

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class EquationBuilder:
    kind: str | None = None
    raw_math: str | None = None
    equation_number: str | None = None   # Always None per spec §17
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    canonical_path: str | None = None