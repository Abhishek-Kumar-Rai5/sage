"""The Citation entity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.support.extracted_field import ExtractedField

__all__ = ["Citation"]


class Citation(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        description="Section 4 authorYYYYabc convention, e.g. smukler2012a."
    )
    author: ExtractedField[str] = Field(description="BETYdb NOT NULL.")
    year: ExtractedField[int] = Field(description="BETYdb NOT NULL.")
    title: ExtractedField[str] = Field(description="BETYdb NOT NULL.")
    persistent_identifier: ExtractedField[str] = Field(
        description=(
            "BETYdb. DOI preferred; ISBN or another persistent identifier "
            "if DOI is unavailable."
        )
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)