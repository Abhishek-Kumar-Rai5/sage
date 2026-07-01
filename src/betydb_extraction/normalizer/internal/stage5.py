"""
Stage 5: Table Internal Structure.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from betydb_extraction.normalizer.builders.base import ClassifiedBlock, Disposition
from betydb_extraction.normalizer.builders.table import (
    TableBuilder,
    TableCellBuilder,
    TableRowBuilder,
    TableRowCellBuilder,
)

_KIND_TABLE_ROW = "table_row"
_KIND_TABLE_ROW_CELL = "table_row_cell"
_KIND_TABLE_CELL = "table_cell"

# Matches a <math ...> ... </math> wrapper tag (case-insensitive, DOTALL so
# it spans multiple lines), capturing its inner content in group 1.
_MATH_WRAPPER_RE = re.compile(
    r"<math\b[^>]*>(.*?)</math\s*>",
    re.IGNORECASE | re.DOTALL,
)

# Header vs. data cell tag names.
_HEADER_CELL_TAGS = {"th"}
_DATA_CELL_TAGS = {"td"}
_CELL_TAGS = _HEADER_CELL_TAGS | _DATA_CELL_TAGS


# ── HTML parsing helpers ──────────────────────────────────────────────────────

def _strip_math_wrapper(html_fragment: str) -> str:
    return _MATH_WRAPPER_RE.sub(lambda m: m.group(1), html_fragment)


def _cell_inner_html(cell_tag: Tag) -> str:
    return cell_tag.decode_contents()


def _parse_rows(raw_html: str) -> list[TableRowBuilder]:

    if not raw_html or not raw_html.strip():
        return []

    soup = BeautifulSoup(raw_html, "html.parser")
    row_builders: list[TableRowBuilder] = []

    for tr_tag in soup.find_all("tr"):
        cell_builders: list[TableRowCellBuilder] = []

        for cell_tag in tr_tag.find_all(list(_CELL_TAGS), recursive=False):
            raw_inner_html = _cell_inner_html(cell_tag)
            text = _strip_math_wrapper(raw_inner_html).strip()
            is_header = cell_tag.name.lower() in _HEADER_CELL_TAGS

            cell_builders.append(
                TableRowCellBuilder(
                    kind=_KIND_TABLE_ROW_CELL,
                    text=text or None,
                    is_header=is_header,
                    structural_notes=None,  # Always None per spec.
                    canonical_path=None,
                    
                )
            )

        row_builders.append(
            TableRowBuilder(
                kind=_KIND_TABLE_ROW,
                cells=cell_builders,
                canonical_path=None,
               
            )
        )

    return row_builders


# ── TABLE_CELL_EVIDENCE (flat cells) helpers ──────────────────────────────────

def _html(block: Any) -> str:
    return getattr(block, "html", "") or ""


def _build_flat_cells_for_wrapper(
    wrapper_block_id: str,
    classified_seq: list[ClassifiedBlock],
) -> list[TableCellBuilder]:
    cell_builders: list[TableCellBuilder] = []

    for cb in classified_seq:
        if cb.disposition != Disposition.TABLE_CELL_EVIDENCE:
            continue
        wrapper_ctx = cb.unwrapped.wrapper_context
        if wrapper_ctx is None or wrapper_ctx.block_id != wrapper_block_id:
            continue

        block = cb.unwrapped.block
        cell_builders.append(
            TableCellBuilder(
                kind=_KIND_TABLE_CELL,
                marker_block_id=block.id,
                text=_html(block) or None,
                bbox=getattr(block, "bbox", None),
                polygon=getattr(block, "polygon", None),
                canonical_path=None,
            
            )
        )

    return cell_builders


# ── Public entry point ────────────────────────────────────────────────────────

def build_table_structure(
    object_builders: list[Any],
    classified_seq: list[ClassifiedBlock],
) -> None:
    block_id_to_index: dict[str, int] = {
        cb.unwrapped.block.id: i
        for i, cb in enumerate(classified_seq)
    }

    for builder in object_builders:
        if not isinstance(builder, TableBuilder):
            continue

        # rows: parsed from raw_html unconditionally (wrapped or bare).
        builder.rows = _parse_rows(builder.raw_html or "")

        # cells: only for wrapped tables; [] for bare tables (resolves MAJOR-4).
        marker_block_id = builder.provenance.marker_block_ids[0]
        shell_index = block_id_to_index.get(marker_block_id)

        wrapper_ctx = None
        if shell_index is not None:
            wrapper_ctx = classified_seq[shell_index].unwrapped.wrapper_context

        if wrapper_ctx is not None:
            builder.cells = _build_flat_cells_for_wrapper(
                wrapper_block_id=wrapper_ctx.block_id,
                classified_seq=classified_seq,
            )
        else:
            builder.cells = []