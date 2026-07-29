"""The Species entity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.support.enums import ProvenanceLabel
from betydb_extraction.ir.support.extracted_field import ExtractedField

__all__ = ["Species"]


class Species(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Section 4. Normalized scientific name.")
    genus: ExtractedField[str] = Field(
        description="BETYdb NOT NULL. Capitalized (BETYdb 14.2)."
    )
    species_epithet: ExtractedField[str] = Field(description="BETYdb NOT NULL.")
    scientific_name: ExtractedField[str] = Field(
        description=(
            "BETYdb scientificname. Must equal genus + \" \" + "
            "species_epithet (+ optional infraspecific text)."
        )
    )
    common_name: ExtractedField[str] | None = Field(default=None)

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)

    @model_validator(mode="after")
    def _check_scientific_name_consistency(self) -> "Species":
        concrete_labels = (ProvenanceLabel.EXTRACTED, ProvenanceLabel.INFERRED)
        if (
            self.genus.provenance_label in concrete_labels
            and self.species_epithet.provenance_label in concrete_labels
            and self.scientific_name.provenance_label in concrete_labels
        ):
            expected_prefix = f"{self.genus.value} {self.species_epithet.value}"
            if not self.scientific_name.value.startswith(expected_prefix):
                raise ValueError(
                    "Species.scientific_name "
                    f"({self.scientific_name.value!r}) must equal genus + "
                    '" " + species_epithet (+ optional infraspecific text); '
                    f"expected it to start with {expected_prefix!r}."
                )
        return self