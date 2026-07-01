"""The Page model.

Implements the Document Schema Specification, Section 8 ("Page"): one
PDF page's structural content, in reading order.
"""
from __future__ import annotations

from typing import Annotated, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.document.equation import Equation
from betydb_extraction.document.figure import Figure
from betydb_extraction.document.footnote import Footnote
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.page_furniture import PageFooter, PageHeader
from betydb_extraction.document.paragraph import Paragraph
from betydb_extraction.document.provenance import StructuralProvenance
from betydb_extraction.document.section import Section
from betydb_extraction.document.table import Table

__all__ = ["Page", "PageChild"]


PageChild = Annotated[
    Union[Section, Paragraph, Table, Figure, Equation, Footnote, PageHeader, PageFooter],
    Field(discriminator="kind"),
]

class Page(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        description=(
            "Deterministic identifier, per Spec Section 2; "
            "canonical_path = '/page/{page_number}'."
        )
    )
    page_number: int = Field(
        ge=0,
        description="Zero-indexed, matching Marker's own page numbering.",
    )
    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the Marker Page block's id]."
    )
    children: list[PageChild] = Field(
        default_factory=list,
        description=(
            "Top-level content of the page, in final reading order (Spec "
            "Section 3.4)."
        ),
    )
    is_front_matter: bool = Field(
        description=(
            "True if this page was identified as publisher wrapper content "
            "(journal cover, 'Submit your article,' ISSN-only content, "
            "etc.) rather than paper body. A Normalizer heuristic output, "
            "not Marker-observed."
        )
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)