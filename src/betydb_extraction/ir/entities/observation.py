"""The Observation entity.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.support.enums import ProvenanceLabel
from betydb_extraction.ir.support.extracted_field import (
    ExtractedField,
    ExtractedReference,
)
from betydb_extraction.ir.support.quantity import QuantityValue
from betydb_extraction.ir.support.statistics import StatisticalSummary
from betydb_extraction.ir.support.temporal import DateRange

__all__ = ["Observation"]


class Observation(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Section 4.")
    dataset_id: str = Field(
        description=(
            "Protocol 6.5. Must equal the enclosing IRDataset.dataset_id "
            "(Section 10.2)."
        )
    )
    citation_id: ExtractedReference = Field(
        description=(
            "Protocol 6.5; BETYdb NOT NULL. Must match the citation_id of "
            "the referenced Treatment (Section 10.2)."
        )
    )
    site_id: ExtractedReference = Field(
        description=(
            "Must match the site_id of the referenced Treatment (Section "
            "10.2)."
        )
    )
    treatment_id: ExtractedReference = Field(
        description="BETYdb singular NOT NULL. Confirmed singular; not a list."
    )
    species_id: ExtractedReference | None = Field(
        default=None,
        description=(
            "Multi-species observations (e.g. intercropping) are not "
            "addressed by either governing source."
        ),
    )
    method_id: ExtractedReference = Field(
        description="Protocol 6.5. Links to Method."
    )
    replicate_id: ExtractedField[str] | None = Field(
        default=None,
        description="Protocol 6.5, 8.3. Plain text, e.g. plot_1, block_a_plot_3.",
    )
    variable_name: ExtractedField[str] = Field(
        description="Protocol 6.5 (trait -> variable). Free text; no controlled vocabulary supplied by either source."
    )
    value: ExtractedField[QuantityValue] = Field(description="Protocol mean -> value.")
    statistical_encoding: ExtractedField[StatisticalSummary] | None = Field(
        default=None, description="Section 6.5."
    )
    reported_effect_scope: ExtractedField[
        Literal["treatment_mean", "aggregated_mean"]
    ] = Field(
        description=(
            "Protocol 7.4, 16.1. Typed directly as a Literal; no separate "
            "enum (Section 3.1)."
        )
    )
    aggregated_over_factors: ExtractedField[list[str]] | None = Field(
        default=None,
        description="Protocol 16.1. See Section 7.7.1 for the required/not-applicable rule.",
    )
    temporal_info: ExtractedField[DateRange] = Field(description="Section 6.4.")
    notes: ExtractedField[str] | None = Field(
        default=None, description="Protocol 6.5."
    )
    is_raw_replicate_level: ExtractedField[bool] = Field(
        description=(
            "Principle P2. Generally independent of reported_effect_scope; "
            "when n = 1 the distinction may coincide, though edge cases "
            "exist."
        )
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)

    @model_validator(mode="after")
    def _check_aggregated_over_factors_rule(self) -> "Observation":
        scope_field = self.reported_effect_scope
        if scope_field.provenance_label != ProvenanceLabel.EXTRACTED:
            return self

        scope = scope_field.value

        if scope == "treatment_mean":
            if self.aggregated_over_factors is None:
                raise ValueError(
                    "Observation.aggregated_over_factors must be set (not "
                    'None) when reported_effect_scope is "treatment_mean".'
                )
            if (
                self.aggregated_over_factors.provenance_label
                != ProvenanceLabel.EXTRACTED
                or self.aggregated_over_factors.value != []
            ):
                raise ValueError(
                    'Observation.aggregated_over_factors is not applicable '
                    'when reported_effect_scope is "treatment_mean"; it '
                    "must be EXTRACTED with an empty list, distinct from "
                    "UNRESOLVED."
                )

        elif scope == "aggregated_mean":
            if self.aggregated_over_factors is None:
                raise ValueError(
                    "Observation.aggregated_over_factors is required "
                    'when reported_effect_scope is "aggregated_mean".'
                )
            if (
                self.aggregated_over_factors.provenance_label
                == ProvenanceLabel.EXTRACTED
                and not self.aggregated_over_factors.value
            ):
                raise ValueError(
                    "Observation.aggregated_over_factors must record which "
                    'factor(s) were collapsed when reported_effect_scope '
                    'is "aggregated_mean"; it must not be an empty list.'
                )

        return self