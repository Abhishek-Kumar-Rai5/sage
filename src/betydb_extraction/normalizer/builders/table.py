"""
Table-related builders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder


@dataclass
class TableRowCellBuilder:
    """One <th> or <td> element parsed from raw_html."""
    kind: str | None = None
    text: str | None = None
    is_header: bool | None = None
    structural_notes: str | None = None   # Always None per spec §5 Stage 5
    canonical_path: str | None = None


@dataclass
class TableRowBuilder:
    """One <tr> element parsed from raw_html."""
    kind: str | None = None
    cells: list[TableRowCellBuilder] = field(default_factory=list)
    canonical_path: str | None = None


@dataclass
class TableCellBuilder:
    kind: str | None = None
    marker_block_id: str | None = None  
    text: str | None = None
    bbox: Any | None = None
    polygon: Any | None = None
    canonical_path: str | None = None


@dataclass
class TableBuilder:
    kind: str | None = None
    raw_html: str | None = None
    caption: Any | None = None
    rows: list[TableRowBuilder] = field(default_factory=list)
    cells: list[TableCellBuilder] = field(default_factory=list)
    footnote_ids: list[str] = field(default_factory=list)
    provenance: ProvenanceBuilder = field(default_factory=ProvenanceBuilder)
    canonical_path: str | None = None
  


  

