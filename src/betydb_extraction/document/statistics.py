from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["Statistics"]


class Statistics(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    page_count: int = Field(ge=0, description="len(pages).")
    section_count: int = Field(
        ge=0, description="Total Section objects across the document."
    )
    paragraph_count: int = Field(ge=0, description="Total Paragraph objects.")
    table_count: int = Field(ge=0, description="Total Table objects.")
    figure_count: int = Field(ge=0, description="Total Figure objects.")
    equation_count: int = Field(ge=0, description="Total Equation objects.")
    footnote_count: int = Field(ge=0, description="Total Footnote objects.")
    reference_count: int = Field(
        ge=0,
        description=(
            "Total Reference objects. As of Version 1.1, Reference objects "
            "are reachable as Section.children members under a References "
            "Section, so this is a true traversal count."
        ),
    )
    unresolved_footnote_count: int = Field(
        ge=0,
        description=(
            "Footnotes whose attached_object_id is None after Normalizer "
            "processing -- a direct, queryable signal of how much of the "
            "geometric-attachment heuristic (empirical finding 3.2) "
            "succeeded on this paper."
        ),
    )

    @model_validator(mode="after")
    def _check_unresolved_does_not_exceed_total(self) -> "Statistics":
        if self.unresolved_footnote_count > self.footnote_count:
            raise ValueError(
                "Statistics.unresolved_footnote_count "
                f"({self.unresolved_footnote_count}) cannot exceed "
                f"footnote_count ({self.footnote_count})."
            )
        return self