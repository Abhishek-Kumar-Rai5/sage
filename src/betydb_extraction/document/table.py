from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from betydb_extraction.document.caption import Caption
from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.provenance import (
    BoundingBox,
    Polygon,
    StructuralProvenance,
)

__all__ = ["Table", "TableCell", "TableRow", "TableRowCell"]


class TableRowCell(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(
        description=(
            "Cell text content from the parsed <th>/<td> element, with any "
            "<math> wrapper tag stripped and its content treated as plain text."
        )
    )
    is_header: bool = Field(
        description="True if the source element was <th>, false for <td>."
    )
    structural_notes: str | None = Field(
        default=None,
        description=(
            "A free-text slot reserved for a Normalizer-attached structural "
            "annotation, most notably a suspected merged-cell placeholder "
            "(Marker silently flattens merged header cells into duplicated "
            "rows with an empty filler cell, with no flag distinguishing this "
            "from a genuinely empty cell). The heuristic for populating this "
            "field is explicitly not decided by the specification -- it is an "
            "open slot reserved so that decision can be made later without a "
            "schema change."
        ),
    )


class TableRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cells: list[TableRowCell] = Field(
        min_length=1,
        description="Ordered left to right per the source <tr> element.",
    )


class TableCell(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    text: str = Field(description="Verbatim Marker TableCell content.")
    bbox: BoundingBox = Field(description="Per-cell geometry.")
    polygon: Polygon = Field(description="Mirrors bbox.")

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)


class Table(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[NodeKind.TABLE] = Field(
        default=NodeKind.TABLE,
        description="Discriminator for Page/Section children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    provenance: StructuralProvenance = Field(
        description=(
            "marker_block_ids = [the Table block's id] (and the TableGroup "
            "id too, if Pattern A)."
        )
    )
    caption: Caption | None = Field(
        default=None,
        description=(
            "None only if no caption-bearing blocks were found adjacent to "
            "the table at all -- not empirically observed in the "
            "representative paper, but not assumed impossible."
        ),
    )
    raw_html: str = Field(
        description=(
            "The Table block's own html field, verbatim -- the complete, "
            "correctly-nested <table>...</table> Marker produces. The source "
            "of truth for logical structure."
        )
    )
    rows: list[TableRow] = Field(
        default_factory=list,
        description=(
            "A structured parse of raw_html's <tr> elements into row "
            "objects, derived from raw_html, not an independent "
            "reconstruction. May be empty."
        ),
    )
    cells: list[TableCell] = Field(
        default_factory=list,
        description=(
            "The flat list of Marker TableCell child blocks, retained only "
            "as evidence/geometry data. May be empty."
        ),
    )
    footnote_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Ids of Footnote objects geometrically attached to this table. "
            "Empty until the Normalizer's bbox-proximity heuristic runs; the "
            "field exists now so that heuristic's output has a defined home "
            "without a later schema change."
        ),
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)