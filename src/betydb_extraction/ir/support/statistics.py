"""StatisticalSummary.

Implements IR Specification Section 6.5 ("StatisticalSummary").
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["StatisticalSummary"]


class StatisticalSummary(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    statistic_name: str = Field(
        description="Free text at the IR layer; constrained during materialization."
    )
    statistic_value: float | str = Field(
        description="Value reported for the statistic."
    )