"""The Paragraph model.

Implements the Document Schema Specification, Section 10 ("Paragraph"):
a single block of body text, the most common leaf content type.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.provenance import StructuralProvenance

__all__ = ["Paragraph"]


class Paragraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[NodeKind.PARAGRAPH] = Field(
        default=NodeKind.PARAGRAPH,
        description="Discriminator for Page/Section children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    text: str = Field(
        description=(
            "The block's inline HTML content from Marker, as-is, including "
            "any inline markup tags."
        )
    )
    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the originating Text/ListItem block's id]."
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)