"""
PageBuilder — mutable accumulator for Schema v1.1 Page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class PageBuilder:
    kind: str | None = None
    page_number: int | None = None
    is_front_matter: bool | None = None
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    children: list[Any] = field(default_factory=list)
    canonical_path: str | None = None
 