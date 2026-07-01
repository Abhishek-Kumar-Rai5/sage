"""
Public API for the Normalizer.
"""
from __future__ import annotations

from betydb_extraction.document.document import Document
from betydb_extraction.marker_adapter.raw_model import MarkerDocument
from betydb_extraction.normalizer.context import NormalizerProcessingContext
from betydb_extraction.normalizer.internal.stage0 import detect_front_matter
from betydb_extraction.normalizer.internal.stage1 import build_page_shells
from betydb_extraction.normalizer.internal.stage1_5 import unwrap_page
from betydb_extraction.normalizer.internal.stage2 import classify_blocks
from betydb_extraction.normalizer.internal.stage3 import build_leaf_builders
from betydb_extraction.normalizer.internal.stage4 import resolve_captions
from betydb_extraction.normalizer.internal.stage5 import build_table_structure
from betydb_extraction.normalizer.internal.stage6 import attach_footnotes
from betydb_extraction.normalizer.internal.stage7 import assemble_section_tree
from betydb_extraction.normalizer.internal.stage8 import assign_reading_order
from betydb_extraction.normalizer.internal.stage9 import compute_canonical_paths
from betydb_extraction.normalizer.internal.stage10 import materialize
from betydb_extraction.normalizer.internal.stage11 import validate_whole_tree
from betydb_extraction.normalizer.internal.stage10 import (
    _compute_document_id,
    _compute_object_id,
)


def normalize(
    marker_document: MarkerDocument,
    source_pdf_identifier: str,
    processing_context: NormalizerProcessingContext,
) -> Document:
    page_blocks = marker_document.pages  # list[MarkerBlock], one per page
    front_matter_flags: dict[int, bool] = detect_front_matter(page_blocks)
    page_builders = build_page_shells(page_blocks, front_matter_flags)
    classified_sequences = []
    flat_builders_per_page = []
    shared_heading_registry: dict = {}

    for page_index, page_block in enumerate(page_blocks):
        page_builder = page_builders[page_index]

        # Stage 1.5 — Wrapper unwrapping
        unwrapped = unwrap_page(page_block.children or [])

        # Stage 2 — Block classification
        classified = classify_blocks(unwrapped, page_index, shared_heading_registry)
        classified_sequences.append(classified)

        # Stage 3 — Leaf builder construction
        flat_builders = build_leaf_builders(
            classified, page_number=page_index
        )
        flat_builders_per_page.append(flat_builders)

        # Stage 4 — Caption resolution
        resolve_captions(flat_builders, classified, page_index)

        # Stage 5 — Table internal structure
        build_table_structure(flat_builders, classified)

        # Stage 6 — Footnote attachment
        attach_footnotes(flat_builders, classified, page_index)
        page_builder.children = flat_builders

    # Stage 7 — Section tree assembly (whole document)

    assemble_section_tree(
        page_builders=page_builders,
        classified_pages=classified_sequences,
    )

    # Stage 8 — Global reading-order assignment (whole document)
    assign_reading_order(page_builders)

    # Stage 9 — Canonical path computation (whole document)
    compute_canonical_paths(page_builders)

    # Stage 10 discards the builder tree.
    stage3_expected_ids: set[str] = _collect_stage3_expected_ids(
        flat_builders_per_page, source_pdf_identifier
    )

    # Stage 10 — Materialization
    document: Document = materialize(
        page_builders=page_builders,
        source_pdf_identifier=source_pdf_identifier,
        processing_context=processing_context,
        classified_pages=classified_sequences,
    )

    # Stage 11 — Whole-tree validation
    validate_whole_tree(
        document=document,
        stage3_expected_ids=stage3_expected_ids,
    )

    return document


# Internal helper — not part of the public contract
def _collect_stage3_expected_ids(
    flat_builders_per_page: list[list],
    source_pdf_identifier: str,
) -> set[str]:
    document_id = _compute_document_id(source_pdf_identifier)
    ids: set[str] = set()
    for page_flat in flat_builders_per_page:
        for builder in page_flat:
            cp = getattr(builder, "canonical_path", None)
            if cp is not None:
                ids.add(_compute_object_id(document_id, cp))
    return ids