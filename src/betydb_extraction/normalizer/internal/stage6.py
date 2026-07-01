"""
Stage 6: Footnote Attachment.
"""
from __future__ import annotations

from typing import Any

from betydb_extraction.normalizer.builders.base import ClassifiedBlock
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.footnote import FootnoteBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.logging_util import (
    log_footnote_attached,
    log_footnote_missing_bbox,
    log_footnote_not_attached,
)

# Candidate target builder types for footnote attachment.
_TargetBuilder = TableBuilder | FigureBuilder


# ── Internal helpers ──────────────────────────────────────────────────────────

def _bbox_y0(bbox: Any) -> float | None:
    if bbox is None:
        return None
    return getattr(bbox, "y0", None)


def _bbox_y1(bbox: Any) -> float | None:
    if bbox is None:
        return None
    return getattr(bbox, "y1", None)


def _marker_block_id(builder: Any) -> str:
    mids = builder.provenance.marker_block_ids
    if not mids:
        raise ValueError(
            f"Stage 6: builder {type(builder).__name__!r} has empty "
            "provenance.marker_block_ids — cannot use as an interim "
            "cross-reference id."
        )
    return mids[0]


def _build_block_id_to_seq_index(
    classified_seq: list[ClassifiedBlock],
) -> dict[str, int]:
    return {
        cb.unwrapped.block.id: i
        for i, cb in enumerate(classified_seq)
    }


def _select_best_candidate(
    footnote_bbox_y0: float,
    candidates: list[_TargetBuilder],
    block_id_to_seq_index: dict[str, int],
) -> _TargetBuilder | None:
    best: _TargetBuilder | None = None
    best_y1: float | None = None
    best_seq_index: int | None = None

    for candidate in candidates:
        candidate_y1 = _bbox_y1(candidate.provenance.bbox)
        if candidate_y1 is None:
            # No bbox on this candidate — cannot be compared; skip it.
            continue
        if not (candidate_y1 < footnote_bbox_y0):
            continue

        candidate_mbid = _marker_block_id(candidate)
        candidate_seq_index = block_id_to_seq_index.get(candidate_mbid)
        if candidate_seq_index is None:
            # A candidate must originate from this page's classified
            # sequence — if it doesn't, that's an internal inconsistency
            # between the object_builders list and classified_seq passed
            # to this call.  Fail loudly rather than silently mis-ordering
            # the tie-break (spec §22 fail-loud philosophy).
            raise ValueError(
                f"Stage 6: candidate {type(candidate).__name__!r} with "
                f"marker_block_id={candidate_mbid!r} was not found in the "
                "classified_seq passed to this call — object_builders and "
                "classified_seq are out of sync for this page."
            )

        if (
            best is None
            or candidate_y1 > best_y1
            or (candidate_y1 == best_y1 and candidate_seq_index < best_seq_index)
        ):
            best = candidate
            best_y1 = candidate_y1
            best_seq_index = candidate_seq_index

    return best


# ── Public entry point ────────────────────────────────────────────────────────

def attach_footnotes(
    object_builders: list[Any],
    classified_seq: list[ClassifiedBlock],
    page_number: int,
) -> None:
    footnotes: list[FootnoteBuilder] = [
        b for b in object_builders if isinstance(b, FootnoteBuilder)
    ]
    candidates: list[_TargetBuilder] = [
        b for b in object_builders if isinstance(b, (TableBuilder, FigureBuilder))
    ]

    if not footnotes:
        return

    block_id_to_seq_index = _build_block_id_to_seq_index(classified_seq)

    for footnote in footnotes:
        footnote_mbid = _marker_block_id(footnote)
        footnote_bbox_y0 = _bbox_y0(footnote.provenance.bbox)

        if footnote_bbox_y0 is None:
            # Missing bbox — attached_object_id stays None; log per spec §23.
            footnote.attached_object_id = None
            log_footnote_missing_bbox(
                marker_block_id=footnote_mbid,
                page_index=page_number,
            )
            continue

        target = _select_best_candidate(
            footnote_bbox_y0=footnote_bbox_y0,
            candidates=candidates,
            block_id_to_seq_index=block_id_to_seq_index,
        )

        if target is None:
            footnote.attached_object_id = None
            log_footnote_not_attached(
                marker_block_id=footnote_mbid,
                page_index=page_number,
            )
            continue

        # Atomic both-sides update, from this single matching result.
        target_mbid = _marker_block_id(target)
        footnote.attached_object_id = target_mbid
        target.footnote_ids = list(target.footnote_ids or []) + [footnote_mbid]

        log_footnote_attached(
            footnote_marker_block_id=footnote_mbid,
            target_marker_block_id=target_mbid,
            target_kind=type(target).__name__,
            page_index=page_number,
        )