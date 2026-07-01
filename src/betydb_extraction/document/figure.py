"""The Figure model.

Implements the Document Schema Specification, Section 13 ("Figure").
"""
from __future__ import annotations
import base64
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from betydb_extraction.document.caption import Caption
from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.identifiers import validate_object_id_shape
from betydb_extraction.document.provenance import StructuralProvenance
__all__ = ["Figure"]
class Figure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal[NodeKind.FIGURE] = Field(
        default=NodeKind.FIGURE,
        description="Discriminator for Page/Section children unions.",
    )
    id: str = Field(description="Deterministic identifier, per Spec Section 2.")
    provenance: StructuralProvenance = Field(
        description=(
            "marker_block_ids = [the Figure block's id] (and FigureGroup id, "
            "if present)."
        )
    )
    caption: Caption | None = Field(default=None)
    image_data: bytes | None = Field(
        default=None,
        description=(
            "Base64-decoded raster image content from Marker's images field, "
            "when present. Serializes as a base64 string in JSON per Spec "
            "Section 19."
        ),
    )
    @field_validator("id")
    @classmethod
    def _check_id_shape(cls, value: str) -> str:
        return validate_object_id_shape(value)

    @field_serializer("image_data", when_used="json")
    def _serialize_image_data(self, value: bytes | None) -> str | None:
        if value is None:
            return None
        return base64.b64encode(value).decode("ascii")

    @field_validator("image_data", mode="before")
    @classmethod
    def _decode_image_data(cls, value):
        # Accepts a base64 string (e.g. when re-hydrating from JSON) or
        # raw bytes (e.g. direct Python construction by the Normalizer)
        # interchangeably, so model_validate_json -> model_validate_json
        # and direct construction both work uniformly.
        if isinstance(value, str):
            return base64.b64decode(value)
        return value