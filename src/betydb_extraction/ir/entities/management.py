"""The Management entity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.support.enums import ProvenanceLabel
from betydb_extraction.ir.support.extracted_field import (
    ExtractedField,
    ExtractedReference,
)
from betydb_extraction.ir.support.quantity import QuantityValue
from betydb_extraction.ir.support.temporal import DateRange

__all__ = ["Management"]


class Management(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        description=(
            "Section 4. {treatment_id}_{event_type}_{ordinal} when no "
            "natural label exists."
        )
    )
    citation_id: ExtractedReference = Field(
        description=(
            "BETYdb managements citation_id NOT NULL. Must match the "
            "citation_id of every Treatment referenced (Section 10.2)."
        )
    )
    treatment_ids: ExtractedField[list[ExtractedReference]] | None = Field(
        default=None,
        description=(
            "BETYdb managements_treatments; non-empty required at export. "
            "May be UNRESOLVED at curation when source scoping is unclear "
            "(P1); non-empty and resolved required at materialization."
        ),
    )
    event_type: ExtractedField[str] = Field(
        description=(
            "PEcAn-aligned free text (Protocol 9.1). Not a closed enum; "
            "BETYdb's own mgmttype enum-vs-lookup choice is unresolved at "
            "the BETYdb level."
        )
    )
    date: ExtractedField[DateRange] = Field(
        description=(
            "Section 6.4. Never INFERRED -- EXTRACTED or UNRESOLVED only "
            "(Protocol 9.2)."
        )
    )
    amount: ExtractedField[QuantityValue] | None = Field(
        default=None,
        description=(
            "Protocol 15.2. Never INFERRED -- EXTRACTED or UNRESOLVED only "
            "(Protocol 9.2)."
        ),
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)

    @model_validator(mode="after")
    def _check_date_and_amount_never_inferred(self) -> "Management":
        if self.date.provenance_label == ProvenanceLabel.INFERRED:
            raise ValueError(
                "Management.date must never be INFERRED -- EXTRACTED or "
                "UNRESOLVED only (Protocol 9.2)."
            )
        if (
            self.amount is not None
            and self.amount.provenance_label == ProvenanceLabel.INFERRED
        ):
            raise ValueError(
                "Management.amount must never be INFERRED -- EXTRACTED or "
                "UNRESOLVED only (Protocol 9.2)."
            )
        return self