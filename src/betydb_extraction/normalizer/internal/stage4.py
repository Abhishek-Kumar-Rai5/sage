"""
Stage 4: Caption Resolution.
"""
from __future__ import annotations

import re
from typing import Any

from betydb_extraction.normalizer.builders.base import ClassifiedBlock, Disposition
from betydb_extraction.normalizer.builders.caption import CaptionBuilder
from betydb_extraction.normalizer.builders.figure import FigureBuilder
from betydb_extraction.normalizer.builders.provenance import ProvenanceBuilder
from betydb_extraction.normalizer.builders.table import TableBuilder
from betydb_extraction.normalizer.logging_util import (
    log_caption_not_resolved,
    log_caption_resolved,
)

# Schema v1.1 discriminated-union literal for Caption.
_KIND_CAPTION = "caption"
_LABEL_PREFIX_RE = re.compile(
    r"^((?:Table|Figure)\s+\d+[\.:]?\s*)",
    re.IGNORECASE,
)

# Trailing-notes trigger (case-sensitive, per spec):
_TRAILING_NOTE_PREFIX = "Note:"

# Dispositions that are transparent to Pattern B adjacency scans:
_TRANSPARENT_DISPOSITIONS: frozenset[Disposition] = frozenset({
    Disposition.PICTURE,
})


# ── Internal helpers ──────────────────────────────────────────────────────────

def _html(block: Any) -> str:
    return getattr(block, "html", "") or ""


def _make_caption_provenance_pattern_a(
    caption_block: Any,
    wrapper_block_id: str,
    page_number: int,
) -> ProvenanceBuilder:
    return ProvenanceBuilder(
        marker_block_ids=[caption_block.id, wrapper_block_id],
        page_number=page_number,
        bbox=getattr(caption_block, "bbox", None),
        contributing_bboxes=None,
        polygon=getattr(caption_block, "polygon", None),
        reading_order_index=None,   # Stage 8
        section_path=[],            # Stage 7
    )


def _make_caption_provenance_pattern_b(
    label_block: Any,
    caption_text_block: Any,
    trailing_notes_block: Any | None,
    page_number: int,
) -> ProvenanceBuilder:
    ids = [label_block.id, caption_text_block.id]
    bboxes = []

    lb_bbox = getattr(label_block, "bbox", None)
    if lb_bbox is not None:
        bboxes.append(lb_bbox)

    ct_bbox = getattr(caption_text_block, "bbox", None)
    if ct_bbox is not None:
        bboxes.append(ct_bbox)

    if trailing_notes_block is not None:
        ids.append(trailing_notes_block.id)
        tn_bbox = getattr(trailing_notes_block, "bbox", None)
        if tn_bbox is not None:
            bboxes.append(tn_bbox)

    return ProvenanceBuilder(
        marker_block_ids=ids,
        page_number=page_number,
        bbox=None,
        contributing_bboxes=bboxes if bboxes else None,
        polygon=None,
        reading_order_index=None,   # Stage 8
        section_path=[],            # Stage 7
    )


def _split_label_and_text_pattern_a(caption_html: str) -> tuple[str | None, str | None]:
    m = _LABEL_PREFIX_RE.match(caption_html)
    if m:
        raw_label = m.group(1).rstrip(". :")
        remainder = caption_html[m.end():].lstrip(". :")
        return (raw_label or None, remainder.strip() or None)
    return (None, caption_html.strip() or None)


# ── Pattern A resolution ──────────────────────────────────────────────────────

def _resolve_pattern_a(
    wrapper_block_id: str,
    classified_seq: list[ClassifiedBlock],
    page_number: int,
) -> CaptionBuilder | None:
    for cb in classified_seq:
        if (
            cb.disposition == Disposition.CAPTION_TEXT
            and cb.unwrapped.wrapper_context is not None
            and cb.unwrapped.wrapper_context.block_id == wrapper_block_id
        ):
            caption_block = cb.unwrapped.block
            caption_html = _html(caption_block)
            label, text = _split_label_and_text_pattern_a(caption_html)
            provenance = _make_caption_provenance_pattern_a(
                caption_block, wrapper_block_id, page_number
            )
            return CaptionBuilder(
                kind=_KIND_CAPTION,
                label=label,
                text=text,
                trailing_notes=None,
                provenance=provenance,
                canonical_path=None,
            )

    return None


# ── Pattern B resolution ──────────────────────────────────────────────────────

def _non_picture_blocks_before(
    classified_seq: list[ClassifiedBlock],
    index: int,
) -> list[tuple[int, ClassifiedBlock]]:
    return [
        (i, cb)
        for i, cb in enumerate(classified_seq[:index])
        if cb.disposition not in _TRANSPARENT_DISPOSITIONS
    ]


def _non_picture_blocks_after(
    classified_seq: list[ClassifiedBlock],
    index: int,
) -> list[tuple[int, ClassifiedBlock]]:
    return [
        (i, cb)
        for i, cb in enumerate(classified_seq[index + 1:], start=index + 1)
        if cb.disposition not in _TRANSPARENT_DISPOSITIONS
    ]


def _resolve_pattern_b(
    shell_index: int,
    classified_seq: list[ClassifiedBlock],
    page_number: int,
    object_kind: str,
    marker_block_id: str,
) -> CaptionBuilder | None:
    # 1. Find immediately preceding non-PICTURE block — must be the caption
    #    text (BODY_PARAGRAPH), the block adjacent to the shell.
    preceding = _non_picture_blocks_before(classified_seq, shell_index)
    if not preceding:
        log_caption_not_resolved(
            object_kind=object_kind,
            marker_block_id=marker_block_id,
            reason="pattern_b: no preceding non-PICTURE block",
        )
        return None

    text_index, text_cb = preceding[-1]
    if text_cb.disposition != Disposition.BODY_PARAGRAPH:
        log_caption_not_resolved(
            object_kind=object_kind,
            marker_block_id=marker_block_id,
            reason=(
                f"pattern_b: immediately preceding non-PICTURE block has "
                f"disposition={text_cb.disposition!r}, expected BODY_PARAGRAPH"
            ),
        )
        return None

    caption_text_block = text_cb.unwrapped.block

    # 2. Find the non-PICTURE block immediately preceding the caption text —
    #    must be CAPTION_LABEL.
    preceding_label = _non_picture_blocks_before(classified_seq, text_index)
    if not preceding_label:
        log_caption_not_resolved(
            object_kind=object_kind,
            marker_block_id=marker_block_id,
            reason="pattern_b: no preceding non-PICTURE block before caption text",
        )
        return None

    label_index, label_cb = preceding_label[-1]
    if label_cb.disposition != Disposition.CAPTION_LABEL:
        log_caption_not_resolved(
            object_kind=object_kind,
            marker_block_id=marker_block_id,
            reason=(
                f"pattern_b: block immediately preceding caption text has "
                f"disposition={label_cb.disposition!r}, expected CAPTION_LABEL"
            ),
        )
        return None

    label_block = label_cb.unwrapped.block

    # 3. Check for optional trailing-notes block immediately after the shell.
    following = _non_picture_blocks_after(classified_seq, shell_index)
    trailing_notes_block: Any | None = None
    if following:
        _, next_cb = following[0]
        next_html = _html(next_cb.unwrapped.block)
        if next_html.startswith(_TRAILING_NOTE_PREFIX):
            trailing_notes_block = next_cb.unwrapped.block

    # 4. Build the CaptionBuilder.
    provenance = _make_caption_provenance_pattern_b(
        label_block=label_block,
        caption_text_block=caption_text_block,
        trailing_notes_block=trailing_notes_block,
        page_number=page_number,
    )
    return CaptionBuilder(
        kind=_KIND_CAPTION,
        label=_html(label_block) or None,
        text=_html(caption_text_block) or None,
        trailing_notes=_html(trailing_notes_block) if trailing_notes_block else None,
        provenance=provenance,
        canonical_path=None,
    )


# ── Public entry point ────────────────────────────────────────────────────────

def resolve_captions(
    object_builders: list[Any],
    classified_seq: list[ClassifiedBlock],
    page_number: int,
) -> None:
    # Build a lookup: Marker block id → index in classified_seq.
    # Used to find the shell's position for Pattern B adjacency scan, and to
    # recover wrapper_context for Pattern A.
    block_id_to_index: dict[str, int] = {
        cb.unwrapped.block.id: i
        for i, cb in enumerate(classified_seq)
    }

    for builder in object_builders:
        if not isinstance(builder, (TableBuilder, FigureBuilder)):
            continue

        # The shell's own Marker id is always marker_block_ids[0] at this
        # point in the pipeline (Stage 3 sets it to exactly [block.id]).
        marker_block_id = builder.provenance.marker_block_ids[0]
        shell_index = block_id_to_index.get(marker_block_id)
        if shell_index is None:
            log_caption_not_resolved(
                object_kind=builder.kind or "unknown",
                marker_block_id=marker_block_id,
                reason="shell block not found in classified_seq",
            )
            builder.caption = None
            continue

        shell_cb = classified_seq[shell_index]
        wrapper_ctx = shell_cb.unwrapped.wrapper_context
        object_kind = builder.kind or "unknown"

        if wrapper_ctx is not None:
            # Pattern A: wrapped (TableGroup or FigureGroup).
            caption = _resolve_pattern_a(
                wrapper_block_id=wrapper_ctx.block_id,
                classified_seq=classified_seq,
                page_number=page_number,
            )
            if caption is not None:
                log_caption_resolved(
                    object_kind=object_kind,
                    marker_block_id=marker_block_id,
                    pattern="A",
                )
            else:
                log_caption_not_resolved(
                    object_kind=object_kind,
                    marker_block_id=marker_block_id,
                    reason="pattern_a: no CAPTION_TEXT sibling found for wrapper_id",
                )
        else:
            # Pattern B: bare (wrapper_context is None).
            caption = _resolve_pattern_b(
                shell_index=shell_index,
                classified_seq=classified_seq,
                page_number=page_number,
                object_kind=object_kind,
                marker_block_id=marker_block_id,
            )
            # Pattern B logs its own failure reason internally; log success here.
            if caption is not None:
                log_caption_resolved(
                    object_kind=object_kind,
                    marker_block_id=marker_block_id,
                    pattern="B",
                )

        builder.caption = caption