"""ExtractedField[T] and ExtractedReference.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from betydb_extraction.ir.support.enums import ProvenanceLabel
from betydb_extraction.ir.support.extraction_source import ExtractionSource

__all__ = ["ExtractedField", "ExtractedReference"]

T = TypeVar("T")


class ExtractedField(BaseModel, Generic[T]):
    """A provenance-wrapped field value.

    IR Spec Section 6.1, Table 4.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: T | None = Field(
        default=None,
        description=(
            "Set when provenance_label is EXTRACTED or INFERRED; None when "
            "UNRESOLVED."
        ),
    )
    provenance_label: ProvenanceLabel = Field(description="IR Spec Section 5.")
    unresolved_reason: str | None = Field(
        default=None,
        description=(
            "Required when UNRESOLVED. Repurposed as an inference-basis "
            "note when INFERRED."
        ),
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Scale pending mentor confirmation (IR Spec Section 11).",
    )
    source: ExtractionSource = Field(description="IR Spec Section 6.2.")

    @model_validator(mode="after")
    def _check_provenance_invariants(self) -> "ExtractedField[T]":
        if self.provenance_label in (
            ProvenanceLabel.EXTRACTED,
            ProvenanceLabel.INFERRED,
        ):
            if self.value is None:
                raise ValueError(
                    "ExtractedField.value must be set when provenance_label "
                    f"is {self.provenance_label.value}."
                )

        if self.provenance_label == ProvenanceLabel.UNRESOLVED:
            if self.value is not None:
                raise ValueError(
                    "ExtractedField.value must be None when provenance_label "
                    "is UNRESOLVED."
                )
            if self.unresolved_reason is None:
                raise ValueError(
                    "ExtractedField.unresolved_reason is required when "
                    "provenance_label is UNRESOLVED."
                )

        if self.provenance_label == ProvenanceLabel.INFERRED:
            if self.unresolved_reason is None:
                raise ValueError(
                    "ExtractedField.unresolved_reason is required as an "
                    "inference-basis note when provenance_label is "
                    "INFERRED."
                )

        return self


class ExtractedReference(BaseModel):
    """A provenance-carrying reference to another entity's text-key id.

    Used directly as an entity field's type when the reference is always
    resolved (e.g. Method.citation_id); wrapped in
    ExtractedField[list[ExtractedReference]] when a set of references may
    itself be UNRESOLVED at curation (e.g. Management.treatment_ids).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_id: str = Field(
        description=(
            "The text-key id (IR Spec Section 4) of the referenced entity."
        )
    )
    source: ExtractionSource = Field(description="IR Spec Section 6.2.")
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Scale pending mentor confirmation (IR Spec Section 11).",
    )