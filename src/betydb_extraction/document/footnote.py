"""The Footnote model.

Implements the Document Schema Specification, Section 15 ("Footnote").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.provenance import StructuralProvenance

__all__ = ["Footnote"]


class Footnote(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[NodeKind.FOOTNOTE] = Field(
        default=NodeKind.FOOTNOTE,
        description="Discriminator for Page/Section children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the Footnote block's id]."
    )
    raw_text: str = Field(description="Verbatim footnote content.")
    attached_object_id: str | None = Field(
        default=None,
        description=(
            "The id of the Table or Figure this footnote was determined to "
            "belong to. None when unresolved -- a legitimate outcome, not an "
            "implementation gap."
        ),
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)