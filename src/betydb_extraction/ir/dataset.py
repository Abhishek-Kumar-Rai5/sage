"""IRDataset: the root aggregate of the Intermediate Representation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from betydb_extraction.ir.entities.citation import Citation
from betydb_extraction.ir.entities.management import Management
from betydb_extraction.ir.entities.method import Method
from betydb_extraction.ir.entities.observation import Observation
from betydb_extraction.ir.entities.site import Site
from betydb_extraction.ir.entities.species import Species
from betydb_extraction.ir.entities.treatment import Treatment
from betydb_extraction.ir.identifiers import validate_text_key_shape
from betydb_extraction.ir.validation.errors import IRDatasetValidationError
from betydb_extraction.ir.validation.referential_integrity import (
    validate_referential_integrity,
)

__all__ = ["IRDataset"]


class IRDataset(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str = Field(
        description=(
            "Section 4. Short source-packet identifier, e.g. "
            "smukler2012_nutrientcycling."
        )
    )
    primary_citation: Citation = Field(description="Section 7.1.")
    sites: list[Site] = Field(default_factory=list, description="Section 7.2.")
    species: list[Species] = Field(
        default_factory=list, description="Section 7.3."
    )
    methods: list[Method] = Field(
        default_factory=list, description="Section 7.4."
    )
    treatments: list[Treatment] = Field(
        default_factory=list, description="Section 7.5."
    )
    managements: list[Management] = Field(
        default_factory=list, description="Section 7.6."
    )
    observations: list[Observation] = Field(
        default_factory=list, description="Section 7.7."
    )

    @field_validator("dataset_id")
    @classmethod
    def _check_dataset_id_shape(cls, value: str) -> str:
        return validate_text_key_shape(value)

    @field_validator(
        "sites",
        "species",
        "methods",
        "treatments",
        "managements",
        "observations",
    )
    @classmethod
    def _sort_entities_by_id(cls, value: list) -> list:
        # IR Spec Section 10 ("Serialization"): entity lists are ordered by
        # id, ascending -- meaningful because ids are human-readable text
        # keys (Section 4).
        return sorted(value, key=lambda entity: entity.id)

    @model_validator(mode="after")
    def _check_whole_graph_invariants(self) -> "IRDataset":
        # IR Spec Section 9.2 ("Whole-Graph (IRDataset)"), Table 19.
        errors = validate_referential_integrity(self)
        if errors:
            raise IRDatasetValidationError(errors)
        return self