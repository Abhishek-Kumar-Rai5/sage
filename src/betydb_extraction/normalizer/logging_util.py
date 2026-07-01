"""
Structured logging helpers for the Normalizer.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("normalizer")


def _emit(level: int, event: str, **fields: Any) -> None:
    logger.log(level, event, extra={"normalizer_fields": fields})


#Stage 0

def log_front_matter_detection(
    page_index: int,
    signals_fired: list[str],
    is_front_matter: bool,
) -> None:
    _emit(
        logging.DEBUG,
        "stage0.front_matter_detection",
        page_index=page_index,
        signals_fired=signals_fired,
        is_front_matter=is_front_matter,
    )


#Stage 2

def log_picture_discarded(marker_block_id: str, page_index: int) -> None:
    _emit(
        logging.INFO,
        "stage2.picture_discarded",
        marker_block_id=marker_block_id,
        page_index=page_index,
    )


#Stage 4

def log_caption_resolved(
    object_kind: str,
    marker_block_id: str,
    pattern: str,
) -> None:
    _emit(
        logging.DEBUG,
        "stage4.caption_resolved",
        object_kind=object_kind,
        marker_block_id=marker_block_id,
        pattern=pattern,
    )


def log_caption_not_resolved(
    object_kind: str,
    marker_block_id: str,
    reason: str,
) -> None:
    _emit(
        logging.INFO,
        "stage4.caption_not_resolved",
        object_kind=object_kind,
        marker_block_id=marker_block_id,
        reason=reason,
    )



def log_footnote_attached(
    footnote_marker_block_id: str,
    target_marker_block_id: str,
    target_kind: str,
    page_index: int,
) -> None:
    _emit(
        logging.DEBUG,
        "stage6.footnote_attached",
        footnote_marker_block_id=footnote_marker_block_id,
        target_marker_block_id=target_marker_block_id,
        target_kind=target_kind,
        page_index=page_index,
    )


def log_footnote_not_attached(
    marker_block_id: str,
    page_index: int,
) -> None:
    _emit(
        logging.INFO,
        "stage6.footnote_not_attached",
        marker_block_id=marker_block_id,
        page_index=page_index,
    )


def log_footnote_missing_bbox(
    marker_block_id: str,
    page_index: int,
) -> None:
    _emit(
        logging.INFO,
        "stage6.footnote_missing_bbox",
        marker_block_id=marker_block_id,
        page_index=page_index,
    )


def log_materialization_complete(
    statistics: dict[str, Any],
    normalizer_version: str,
) -> None:
    _emit(
        logging.INFO,
        "stage10.materialization_complete",
        statistics=statistics,
        normalizer_version=normalizer_version,
    )

def log_error_context(
    stage: str,
    marker_block_id: str | None,
    page_index: int | None,
    message: str,
) -> None:
    _emit(
        logging.ERROR,
        "normalizer.error",
        stage=stage,
        marker_block_id=marker_block_id,
        page_index=page_index,
        message=message,
    )