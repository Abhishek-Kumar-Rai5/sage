"""The PageHeader and PageFooter models.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.provenance import StructuralProvenance
__all__ = ["PageFooter", "PageHeader"]
class PageHeader(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal[NodeKind.PAGE_HEADER] = Field(
        default=NodeKind.PAGE_HEADER,
        description="Discriminator for Page children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the PageHeader block's id]."
    )
    raw_text: str = Field(description="Verbatim content.")
    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)
class PageFooter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal[NodeKind.PAGE_FOOTER] = Field(
        default=NodeKind.PAGE_FOOTER,
        description="Discriminator for Page children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    provenance: StructuralProvenance = Field(
        description="marker_block_ids = [the PageFooter block's id]."
    )
    raw_text: str = Field(description="Verbatim content.")
    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)