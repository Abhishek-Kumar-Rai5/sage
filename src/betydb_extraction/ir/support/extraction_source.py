"""ExtractionSource and SourceLocator variants.

Implements IR Specification Section 6.2 ("ExtractionSource / SourceLocator").
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ExtractionSource",
    "FigureLocator",
    "ObjectLocator",
    "SourceLocator",
    "TableLocator",
    "TextLocator",
]


class TextLocator(BaseModel):
    """Locates a value within running body text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["text"] = Field(
        default="text", description="Discriminator for SourceLocator variants."
    )
    quoted_text: str = Field(
        description="The verbatim text span the value was taken from."
    )


class TableLocator(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["table"] = Field(
        default="table", description="Discriminator for SourceLocator variants."
    )
    table_id: str = Field(
        description="The id of the Document Table object the value came from."
    )
    row_label: str | None = Field(
        default=None, description="Optional row-level addressing."
    )
    column_label: str | None = Field(
        default=None, description="Optional column-level addressing."
    )


class FigureLocator(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["figure"] = Field(
        default="figure", description="Discriminator for SourceLocator variants."
    )
    figure_id: str = Field(
        description="The id of the Document Figure object the value came from."
    )
    panel_label: str = Field(
        description="Free-text panel identifier, e.g. 'panel B'."
    )


class ObjectLocator(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["object"] = Field(
        default="object", description="Discriminator for SourceLocator variants."
    )
    object_id: str = Field(
        description="The id of the Document object the value came from."
    )


SourceLocator = Annotated[
    Union[TextLocator, TableLocator, FigureLocator, ObjectLocator],
    Field(discriminator="kind"),
]


class ExtractionSource(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_document_id: str = Field(
        description="Links to Document Schema Document.id."
    )
    page_number: int = Field(description="The page the value originates from.")
    section_path: list[str] = Field(
        default_factory=list, description="May be empty."
    )
    locators: list[SourceLocator] = Field(
        min_length=1,
        description="TextLocator | TableLocator | FigureLocator | ObjectLocator.",
    )
    raw_excerpt: str | None = Field(default=None)
    notes: str | None = Field(
        default=None,
        description="Sufficient for a second curator to retrace the value.",
    )