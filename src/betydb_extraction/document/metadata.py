"""The Metadata model.

Implements the Document Schema Specification, Section 5 ("Metadata"):
bibliographic and identification facts about the paper, to the extent
they are structurally recoverable.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Metadata"]


class Metadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str | None = Field(
        default=None,
        description=(
            "Taken verbatim from the first/top-level SectionHeader or "
            "title-styled block on the front matter page, if structurally "
            "identifiable."
        ),
    )
    page_count: int = Field(
        ge=0,
        description=(
            "Count of Page objects. Redundant with len(Document.pages) but "
            "kept as an explicit field since Statistics is meant to hold "
            "derived counts, while this is a basic identifying fact worth "
            "surfacing without traversing the tree."
        ),
    )
    has_front_matter_page: bool = Field(
        description=(
            "Whether any page was structurally flagged as publisher wrapper "
            "content. Aggregates Page.is_front_matter (Section 8) across all "
            "pages."
        )
    )