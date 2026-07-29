"""DateRange.

Implements IR Specification Section 6.4 ("DateRange").
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["DateRange"]


class DateRange(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    earliest: date | None = Field(
        default=None,
        description="Blank together with latest when relative_timing is used.",
    )
    latest: date | None = Field(default=None)
    reported_text: str = Field(description="Verbatim as written.")
    relative_timing: str | None = Field(
        default=None,
        description=(
            "E.g. before_planting, after_harvest, at_planting, at_harvest. "
            "Open vocabulary."
        ),
    )
    relative_timing_days: int | None = Field(
        default=None,
        description="Numeric offset, only when explicitly reported.",
    )

    @model_validator(mode="after")
    def _check_representation_invariants(self) -> "DateRange":
        has_earliest = self.earliest is not None
        has_latest = self.latest is not None

        if has_earliest != has_latest:
            raise ValueError(
                "DateRange: earliest and latest must be set together."
            )

        if has_earliest and has_latest and self.earliest > self.latest:
            raise ValueError(
                f"DateRange: earliest ({self.earliest}) must not be after "
                f"latest ({self.latest})."
            )

        has_interval = has_earliest and has_latest
        if has_interval and self.relative_timing is not None:
            raise ValueError(
                "DateRange may not set both an earliest/latest interval and "
                "relative_timing simultaneously."
            )

        return self