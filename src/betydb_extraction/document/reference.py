"""The Reference model.

Implements the Document Schema Specification v1.1, Section 16
("Reference (Bibliography Entry)").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.provenance import StructuralProvenance

__all__ = ["Reference"]


class Reference(BaseModel):
    """One bibliography entry."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    kind: Literal[NodeKind.REFERENCE] = Field(
        default=NodeKind.REFERENCE,
        description="Discriminator for Section.children.",
    )

    id: str = Field(
        description="Deterministic identifier, per Spec Section 2."
    )

    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the ListItem block's id]."
    )

    raw_text: str = Field(
        description=(
            "Verbatim reference entry text, including any inline markup "
            "Marker preserved."
        )
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)