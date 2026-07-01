from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class SectionBuilder:
    kind: str | None = None
    heading_text: str | None = None
    # depth and parent are internal assembly aids; not in Schema v1.1.
    depth: int | None = None
    parent_section_builder: "SectionBuilder | None" = field(
        default=None, repr=False, compare=False
    )
    children: list[Any] = field(default_factory=list)
    # INVARIANT: heading_marker_block_id must always equal
    # provenance.marker_block_ids[0]. Both are set together, exactly once,
    # at the single call site in Stage 7 Step 1 that constructs this
    # SectionBuilder. Never set one without the other, and never mutate
    # either independently afterward — Stage 9's canonical_path
    # ({page_canonical_path}/section/{heading_marker_block_id}) and this
    # builder's provenance must stay derived from the same source id.
    heading_marker_block_id: str | None = None
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    canonical_path: str | None = None