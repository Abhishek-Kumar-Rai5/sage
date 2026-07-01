"""Foundational supporting value objects: geometry and provenance.

Implements the Document Schema Specification, Section 3 ("Foundational
Supporting Types"): ``BoundingBox`` (3.1), ``Polygon`` (3.2), and
``StructuralProvenance`` (3.3). 
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["BoundingBox", "Polygon", "StructuralProvenance"]


class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    x0: float = Field(description="Left edge.")
    y0: float = Field(description="Top edge.")
    x1: float = Field(description="Right edge.")
    y1: float = Field(description="Bottom edge.")

    @model_validator(mode="after")
    def _check_box_is_not_inverted(self) -> "BoundingBox":
        if self.x1 < self.x0:
            raise ValueError(
                f"BoundingBox is inverted on the x-axis: x1={self.x1} < x0={self.x0}"
            )
        if self.y1 < self.y0:
            raise ValueError(
                f"BoundingBox is inverted on the y-axis: y1={self.y1} < y0={self.y0}"
            )
        return self


class Polygon(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    points: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ] = Field(description="Exactly four (x, y) corner points, as emitted by Marker.")


class StructuralProvenance(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    marker_block_ids: list[str] = Field(
        min_length=1,
        description=(
            "The originating Marker block id(s), e.g. ['/page/7/Table/2']. "
            "A list rather than a single value because some Document objects "
            "(e.g. a normalized Caption under Pattern B) are synthesized from "
            "more than one Marker block."
        ),
    )
    page_number: int = Field(
        description=(
            "The PDF page this object originates from. For objects synthesized "
            "from multiple blocks, the page of the primary/first contributing "
            "block."
        )
    )
    bbox: BoundingBox | None = Field(
        default=None,
        description=(
            "Present for an object with a single, well-defined originating "
            "region. Mutually exclusive with contributing_bboxes."
        ),
    )
    contributing_bboxes: list[BoundingBox] | None = Field(
        default=None,
        description=(
            "Used instead of bbox when more than one Marker block contributes "
            "geometry, preserving each box rather than collapsing them into a "
            "single misleading region. Mutually exclusive with bbox."
        ),
    )
    polygon: Polygon | None = Field(
        default=None,
        description="Mirrors bbox's optionality logic.",
    )
    reading_order_index: int = Field(
        ge=0,
        description=(
            "The object's position in the document's global linear reading "
            "order (Spec Section 3.4), recomputed by the Normalizer from final "
            "tree position -- never copied from a Marker id's trailing index "
            "number, which was empirically confirmed non-monotonic with true "
            "reading order."
        ),
    )
    section_path: list[str] = Field(
        default_factory=list,
        description=(
            "The chain of governing SectionHeader Marker-block ids, ordered "
            "outermost to innermost, derived from Marker's own "
            "section_hierarchy map (Spec Section 3.5). Empty only for objects "
            "outside any section (e.g. a journal wrapper page's Picture)."
        ),
    )

    @model_validator(mode="after")
    def _check_bbox_xor_contributing_bboxes(self) -> "StructuralProvenance":
        if self.bbox is not None and self.contributing_bboxes is not None:
            raise ValueError(
                "StructuralProvenance may not set both 'bbox' and "
                "'contributing_bboxes' -- exactly one geometric claim about "
                "this object's origin is permitted, or neither when no "
                "recoverable geometry exists."
            )
        return self