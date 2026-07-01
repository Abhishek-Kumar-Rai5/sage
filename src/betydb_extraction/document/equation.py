"""The Equation model.

Implements the Document Schema Specification, Section 14 ("Equation").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.provenance import StructuralProvenance

__all__ = ["Equation"]


class Equation(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[NodeKind.EQUATION] = Field(
        default=NodeKind.EQUATION,
        description="Discriminator for Page/Section children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the Equation block's id]."
    )
    raw_math: str = Field(
        description=(
            "The verbatim MathML-ish <math> content, including any equation "
            "number embedded inline."
        )
    )
    equation_number: str | None = Field(
        default=None,
        description=(
            "A slot for the parsed-out equation number, e.g. '1'. Population "
            "logic is out of scope for this layer."
        ),
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)