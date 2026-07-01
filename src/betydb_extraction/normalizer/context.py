from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NormalizerProcessingContext:
    marker_version: str
    """Version string of the Marker run that produced the MarkerDocument."""

    normalizer_version: str
    """Semantic version of this Normalizer code."""

    source_marker_artifact_ref: str
    """Path or content hash identifying the Raw Marker Model JSON file."""

    processed_at: datetime
    """Wall-clock UTC datetime of this materialization. Must be timezone-aware UTC."""