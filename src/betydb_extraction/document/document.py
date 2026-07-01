"""The Document model.

Implements the Document Schema Specification, Section 4 ("Document"): the
root container for one processed paper.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from betydb_extraction.document.identifiers import validate_document_id_shape
from betydb_extraction.document.metadata import Metadata
from betydb_extraction.document.page import Page
from betydb_extraction.document.processing_metadata import ProcessingMetadata
from betydb_extraction.document.statistics import Statistics

__all__ = ["Document"]


class Document(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="document_id, per Spec Section 2.")
    source_pdf_identifier: str = Field(
        description=(
            "The stable external identifier used to compute id (DOI or "
            "content hash). Stored explicitly so the id's derivation is "
            "independently checkable, not just trusted."
        )
    )
    metadata: Metadata = Field(description="Spec Section 5.")
    processing_metadata: ProcessingMetadata = Field(description="Spec Section 6.")
    statistics: Statistics = Field(description="Spec Section 7.")
    pages: list[Page] = Field(
        min_length=1,
        description=(
            "Ordered by page number ascending; this ordering is also the "
            "top level of global reading order."
        ),
    )

    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_document_id_shape(value)

    @model_validator(mode="after")
    def _check_pages_sorted_and_unique(self) -> "Document":
        page_numbers = [page.page_number for page in self.pages]

        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError(
                "Document.pages contains duplicate page_number values; "
                "each page must have a unique page_number."
            )

        if page_numbers != sorted(page_numbers):
            raise ValueError(
                "Document.pages must be ordered ascending by page_number. "
                "A Marker-side page omission (a gap in the sequence) is "
                "permitted and preserved, not silently re-numbered -- but "
                "the list order itself must still be ascending."
            )

        return self