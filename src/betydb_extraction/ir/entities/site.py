"""The Site entity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.support.extracted_field import ExtractedField
from betydb_extraction.ir.support.quantity import QuantityValue

__all__ = ["Site"]


class Site(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Section 4. Source-facing label.")
    name: ExtractedField[str] = Field(
        description="BETYdb sitename, unique NOT NULL Required minimum."
    )
    latitude: ExtractedField[QuantityValue] | None = Field(
        default=None,
        description=(
            "BETYdb lat NOT NULL at export. May be UNRESOLVED at curation; "
            "resolved at materialization."
        ),
    )
    longitude: ExtractedField[QuantityValue] | None = Field(
        default=None,
        description="BETYdb lon NOT NULL at export. Same treatment as latitude.",
    )
    country: ExtractedField[str] | None = Field(
        default=None, description="Protocol 6.2."
    )
    state_or_region: ExtractedField[str] | None = Field(
        default=None, description="Protocol 6.2."
    )
    nearest_city: ExtractedField[str] | None = Field(
        default=None, description="Protocol 6.2."
    )
    elevation: ExtractedField[QuantityValue] | None = Field(
        default=None, description="Protocol 6.2."
    )
    soil_context: ExtractedField[str] | None = Field(
        default=None,
        description="Free text. No further decomposition specified.",
    )
    description: ExtractedField[str] | None = Field(
        default=None, description="Catch-all."
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)