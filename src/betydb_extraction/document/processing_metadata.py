"""The ProcessingMetadata model.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ProcessingMetadata"]


class ProcessingMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    marker_version: str = Field(
        description=(
            "Verbatim from Marker's own output metadata, if present; "
            "otherwise the version string of the Marker invocation recorded "
            "by the adapter."
        )
    )
    normalizer_version: str = Field(
        description=(
            "Semantic version of the Normalizer code that produced this "
            "Document Object. Required so a future schema/logic change is "
            "always attributable."
        )
    )
    processed_at: datetime = Field(
        description=(
            "Wall-clock time of this materialization, ISO 8601 UTC. "
            "Explicitly not part of id computation (Section 2) -- recorded "
            "for audit/debugging only."
        )
    )
    source_marker_artifact_ref: str = Field(
        description=(
            "A path or content hash identifying the exact Raw Marker Model "
            "JSON file this Document Object was normalized from, satisfying "
            "the 'Document has no own provenance' note in Section 4 by "
            "pointing at the file-level artifact instead of a block-level "
            "one."
        )
    )

    @field_validator("processed_at")
    @classmethod
    def _check_processed_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "ProcessingMetadata.processed_at must be timezone-aware "
                "(ISO 8601 UTC per Spec Section 19); got a naive datetime."
            )
        if value.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError(
                "ProcessingMetadata.processed_at must be UTC per Spec "
                f"Section 19; got offset {value.utcoffset()}."
            )
        return value