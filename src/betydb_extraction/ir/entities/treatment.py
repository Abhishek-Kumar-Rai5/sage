"""The Treatment entity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.support.extracted_field import (
    ExtractedField,
    ExtractedReference,
)

__all__ = ["Treatment"]


class Treatment(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        description="Section 4. Unique within citation_id (Section 10.2)."
    )
    citation_id: ExtractedReference = Field(
        description=(
            "BETYdb citations_treatments. Must match the citation of the "
            "Site it is scoped to, per Section 10.2."
        )
    )
    site_id: ExtractedReference = Field(description="")
    name: ExtractedField[str] = Field(
        description='"Recognizable from source."'
    )
    definition: ExtractedField[str] = Field(
        description="BETYdb field name. Renamed from description to match BETYdb exactly."
    )
    control_status: ExtractedField[bool] | None = Field(
        default=None,
        description=(
            "BETYdb control NOT NULL at export. May be UNRESOLVED at "
            "curation."
        ),
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)