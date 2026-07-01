from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from betydb_extraction.document.provenance import StructuralProvenance

__all__ = ["Caption"]


class Caption(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str | None = Field(
        default=None,
        description=(
            "E.g. 'Table 3' or 'Figure 1'. Present whenever a Caption block "
            "(Pattern A) or a SectionHeader label block (Pattern B) was "
            "found."
        ),
    )
    text: str | None = Field(
        default=None,
        description=(
            "The descriptive caption sentence. From the Caption block's "
            "content (Pattern A) or the Text block immediately following "
            "the label (Pattern B)."
        ),
    )
    trailing_notes: str | None = Field(
        default=None,
        description=(
            "The trailing 'Note: ...' Text block sometimes observed "
            "immediately after a Table, distinct from both label/text and "
            "from Footnote objects (Section 15). Kept as its own field "
            "because it was empirically observed to be part of the caption "
            "apparatus, not body text, but also not a true Marker Footnote "
            "block."
        ),
    )
    provenance: StructuralProvenance = Field(
        description=(
            "marker_block_ids lists every contributing Marker block (one "
            "for Pattern A's single Caption block; two or three for "
            "Pattern B's SectionHeader + Text + optional trailing Text). "
            "Uses contributing_bboxes rather than a single bbox whenever "
            "more than one block contributes, since collapsing "
            "non-adjacent regions into one bbox would misrepresent the "
            "geometry."
        )
    )