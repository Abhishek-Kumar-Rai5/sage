"""QuantityValue.

Implements IR Specification Section 6.3 ("QuantityValue").
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["QuantityValue"]


class QuantityValue(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    reported_text: str = Field(
        description='Verbatim, e.g. "3.2", "trace", "<0.1".'
    )
    reported_numeric_value: float | None = Field(
        default=None,
        description="Populated only when reported_text parses cleanly.",
    )
    reported_units: str = Field(description="Verbatim, as published.")
    unit_basis_notes: str | None = Field(
        default=None,
        description="Wet/dry basis, concentration vs. stock, depth interval.",
    )
    converted_value: float | None = Field(
        default=None,
        description="Only if a transformation was unavoidable during curation.",
    )
    converted_units: str | None = Field(
        default=None, description="Required if converted_value is set."
    )
    conversion_formula: str | None = Field(
        default=None, description="Required if converted_value is set."
    )
    conversion_rationale: str | None = Field(
        default=None, description="Required if converted_value is set."
    )

    @model_validator(mode="after")
    def _check_conversion_fields_present_together(self) -> "QuantityValue":
        if self.converted_value is not None:
            missing = [
                name
                for name, value in (
                    ("converted_units", self.converted_units),
                    ("conversion_formula", self.conversion_formula),
                    ("conversion_rationale", self.conversion_rationale),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "QuantityValue.converted_value is set, so the "
                    f"following fields are also required: {', '.join(missing)}."
                )
        return self