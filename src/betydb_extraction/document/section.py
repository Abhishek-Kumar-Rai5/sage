"""The Section model.

Implements the Document Schema Specification, Section 9 ("Section")
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.equation import Equation
from betydb_extraction.document.figure import Figure
from betydb_extraction.document.footnote import Footnote
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.paragraph import Paragraph
from betydb_extraction.document.provenance import StructuralProvenance
from betydb_extraction.document.table import Table
from betydb_extraction.document.reference import Reference

__all__ = ["Section", "SectionChild"]


class Section(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[NodeKind.SECTION] = Field(
        default=NodeKind.SECTION,
        description="Discriminator for Page/Section children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    heading_text: str = Field(
        description="Verbatim text of the governing SectionHeader block."
    )
    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the SectionHeader block's id]."
    )
    depth: int = Field(
        ge=0,
        description=(
            "Position of this section's heading in the ordered section_path "
            "list, zero-indexed from the outermost heading on the "
            "page/document."
        ),
    )
    children: list["SectionChild"] = Field(
        default_factory=list,
        description=(
            "Nested sub-sections and content governed by this heading, in "
            "reading order."
        ),
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)


SectionChild = Annotated[
    Union[
        Section,
        Paragraph,
        Table,
        Figure,
        Equation,
        Footnote,
        Reference,
    ],
    Field(discriminator="kind"),
]

Section.model_rebuild()