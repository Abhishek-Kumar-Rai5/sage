"""The Method entity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.support.extracted_field import (
    ExtractedField,
    ExtractedReference,
)

__all__ = ["Method"]


class Method(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Section 4, e.g. soc_dry_combustion.")
    citation_id: ExtractedReference = Field(
        description="Protocol 6.4. May differ from the paper's primary citation."
    )
    name: ExtractedField[str] = Field(
        description=(
            "Protocol 6.4. Canonical short name. Controlled vocabulary "
            "maintained through curation; not predetermined at the IR "
            "layer."
        )
    )
    description: ExtractedField[str] = Field(
        description=(
            "Protocol 6.4. Basis distinctions (dry/wet, flux-chamber vs. "
            "inferred, etc.) are recorded here as free text, not as "
            "separate fields."
        )
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)