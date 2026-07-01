from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from betydb_extraction.marker_adapter.raw_model import MarkerBlock  # adjust path

# ── Wrapper unwrapping types (Stage 1.5) ─────────────────────────────────────

@dataclass(frozen=True)
class WrapperContext:
    wrapper_type: str
    block_id: str

@dataclass(frozen=True)
class UnwrappedBlock:
    """
    A single Marker block after Stage 1.5 flattening, paired with its
    wrapper provenance (None if it was a direct page child).
    """
    block: "MarkerBlock"
    wrapper_context: WrapperContext | None


# ── Disposition enum (Stage 2) ────────────────────────────────────────────────

class Disposition(str, Enum):
    """
    Classification tags assigned by Stage 2.

    Every value maps to exactly one processing path in Stages 3–7.
    The complete mapping is the Stage 2 classification table in spec §5.
    """
    GENUINE_SECTION_HEADER = "GENUINE_SECTION_HEADER"
    CAPTION_LABEL          = "CAPTION_LABEL"
    BODY_PARAGRAPH         = "BODY_PARAGRAPH"
    REFERENCE_ENTRY        = "REFERENCE_ENTRY"
    TABLE_SHELL            = "TABLE_SHELL"
    FIGURE_SHELL           = "FIGURE_SHELL"
    CAPTION_TEXT           = "CAPTION_TEXT"
    TABLE_CELL_EVIDENCE    = "TABLE_CELL_EVIDENCE"
    EQUATION               = "EQUATION"
    FOOTNOTE               = "FOOTNOTE"
    PAGE_HEADER            = "PAGE_HEADER"
    PAGE_FOOTER            = "PAGE_FOOTER"
    PICTURE                = "PICTURE"



@dataclass(frozen=True)
class ClassifiedBlock:
    """
    An UnwrappedBlock paired with its Stage 2 disposition tag.
    All stages after Stage 2 work against lists of ClassifiedBlocks.
    """
    unwrapped: UnwrappedBlock
    disposition: Disposition