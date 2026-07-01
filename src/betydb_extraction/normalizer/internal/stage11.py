"""
Stage 11: Whole-Tree Validation.
"""

from __future__ import annotations

import logging
from typing import Any

from betydb_extraction.normalizer.errors import WholeTreeInvariantViolationError

logger = logging.getLogger(__name__)


def _iter_all_objects(document: Any) -> list[Any]:
    result: list[Any] = []

    def _walk(items: list[Any]) -> None:
        for item in items:
            result.append(item)
            t = type(item).__name__
            if t == "Section":
                _walk(item.children)
            elif t == "Table":
                if item.caption is not None:
                    result.append(item.caption)
                for row in (item.rows or []):
                    result.append(row)
                    for cell in (row.cells or []):
                        result.append(cell)
                for tc in (item.cells or []):
                    result.append(tc)
            elif t == "Figure":
                if item.caption is not None:
                    result.append(item.caption)

    for page in document.pages:
        result.append(page)
        _walk(page.children)

    return result


def _iter_leaf_objects(document: Any) -> list[Any]:
    result: list[Any] = []

    def _walk(items: list[Any]) -> None:
        for item in items:
            result.append(item)
            t = type(item).__name__
            if t == "Section":
                _walk(item.children)

    for page in document.pages:
        result.append(page)
        _walk(page.children)

    return result


def _iter_objects_with_ancestor_chains(document: Any) -> list[tuple[Any, list[str]]]:
    result: list[tuple[Any, list[str]]] = []

    def _walk(items: list[Any], ancestor_chain: list[str]) -> None:
        for item in items:
            t = type(item).__name__
            if t == "Section":
                result.append((item, list(ancestor_chain)))
                _walk(item.children, ancestor_chain + [item.id])
            else:
                result.append((item, list(ancestor_chain)))
                if t == "Table" and item.caption is not None:
                    result.append((item.caption, list(ancestor_chain)))
                elif t == "Figure" and item.caption is not None:
                    result.append((item.caption, list(ancestor_chain)))

    for page in document.pages:
        _walk(page.children, [])

    return result


def _check_invariant_1(document: Any) -> None:
    items = _iter_leaf_objects(document)
    prev = -1
    offending: list[str] = []
    for item in items:
        roi = getattr(getattr(item, "provenance", None), "reading_order_index", None)
        if roi is None:
            offending.append(getattr(item, "id", "<no-id>"))
            continue
        if roi <= prev:
            offending.append(getattr(item, "id", "<no-id>"))
        prev = roi

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=1,
            description="reading_order_index is not strictly increasing",
            offending_object_ids=offending,
        )


def _check_invariant_2(document: Any, all_objects: list[Any]) -> None:
    table_figure_ids: set[str] = {
        obj.id
        for obj in all_objects
        if type(obj).__name__ in {"Table", "Figure"}
    }
    offending: list[str] = []
    for obj in all_objects:
        if type(obj).__name__ != "Footnote":
            continue
        aid = obj.attached_object_id
        if aid is not None and aid not in table_figure_ids:
            offending.append(obj.id)

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=2,
            description=(
                "Footnote.attached_object_id does not match any Table or Figure id"
            ),
            offending_object_ids=offending,
        )


def _check_invariant_3(document: Any, all_objects: list[Any]) -> None:
    footnote_by_id: dict[str, Any] = {
        obj.id: obj
        for obj in all_objects
        if type(obj).__name__ == "Footnote"
    }
    offending: list[str] = []
    for obj in all_objects:
        if type(obj).__name__ != "Table":
            continue
        for fid in (obj.footnote_ids or []):
            fn = footnote_by_id.get(fid)
            if fn is None or fn.attached_object_id != obj.id:
                offending.append(obj.id)
                break

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=3,
            description="Footnote ↔ Table symmetry violated",
            offending_object_ids=offending,
        )


def _check_invariant_4(document: Any) -> None:
    pairs = _iter_objects_with_ancestor_chains(document)
    offending: list[str] = []

    for obj, real_ancestor_chain in pairs:
        prov = getattr(obj, "provenance", None)
        if prov is None:
            continue

        stored_path: list[str] = list(
            getattr(prov, "section_path", []) or []
        )

        if stored_path == real_ancestor_chain:
            continue
 
         # TEMP DIAGNOSTIC — remove after root cause found
        print(f"MISMATCH obj={type(obj).__name__} id={getattr(obj, 'id', '<no-id>')}")
        print(f"  stored_path = {stored_path}")
        print(f"  real_chain  = {real_ancestor_chain}")

        offending.append(getattr(obj, "id", "<no-id>"))

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=4,
            description=(
                "section_path does not exactly match the object's real "
                "ancestor Section chain (id sequence, order, and length "
                "must match exactly)"
            ),
            offending_object_ids=offending,
        )


def _check_invariant_5(all_objects: list[Any]) -> None:
    seen: dict[str, str] = {}
    offending: list[str] = []
    for obj in all_objects:
        oid = getattr(obj, "id", None)
        if oid is None:
            continue
        if oid in seen:
            offending.append(oid)
        else:
            seen[oid] = type(obj).__name__

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=5,
            description="Duplicate id values found in the tree",
            offending_object_ids=offending,
        )


def _check_invariant_6(document: Any) -> None:
    page_numbers = [p.page_number for p in document.pages]
    offending: list[str] = []
    for i in range(1, len(page_numbers)):
        if page_numbers[i] <= page_numbers[i - 1]:
            offending.append(str(page_numbers[i]))

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=6,
            description="Document.pages is not strictly ascending by page_number",
            offending_object_ids=offending,
        )


def _check_invariant_7(document: Any) -> None:
    counts: dict[str, int] = {
        "page_count": len(document.pages),
        "section_count": 0,
        "paragraph_count": 0,
        "table_count": 0,
        "figure_count": 0,
        "equation_count": 0,
        "footnote_count": 0,
        "unresolved_footnote_count": 0,
        "reference_count": 0,
    }

    def _walk(items: list[Any]) -> None:
        for item in items:
            t = type(item).__name__
            if t == "Section":
                counts["section_count"] += 1
                _walk(item.children)
            elif t == "Paragraph":
                counts["paragraph_count"] += 1
            elif t == "Table":
                counts["table_count"] += 1
            elif t == "Figure":
                counts["figure_count"] += 1
            elif t == "Equation":
                counts["equation_count"] += 1
            elif t == "Footnote":
                counts["footnote_count"] += 1
                if item.attached_object_id is None:
                    counts["unresolved_footnote_count"] += 1
            elif t == "Reference":
                counts["reference_count"] += 1

    for page in document.pages:
        _walk(page.children)

    stats = document.statistics
    offending: list[str] = []
    for field_name, expected in counts.items():
        actual = getattr(stats, field_name, None)
        if actual != expected:
            offending.append(
                f"{field_name}: expected={expected} actual={actual}"
            )

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=7,
            description="Statistics counts do not match independent re-traversal: "
            + "; ".join(offending),
            offending_object_ids=[],
        )


def _check_invariant_8(
    document: Any,
    all_objects: list[Any],
    stage3_expected_ids: set[str],
) -> None:
    tree_ids: dict[str, int] = {}
    for obj in all_objects:
        oid = getattr(obj, "id", None)
        if oid is not None:
            tree_ids[oid] = tree_ids.get(oid, 0) + 1

    missing = stage3_expected_ids - set(tree_ids)
    duplicated = {
        oid for oid, count in tree_ids.items()
        if oid in stage3_expected_ids and count > 1
    }
    offending = list(missing) + list(duplicated)

    if offending:
        raise WholeTreeInvariantViolationError(
            invariant_number=8,
            description=(
                "Stage-3 builders missing from tree or duplicated: "
                f"missing={len(missing)} duplicated={len(duplicated)}"
            ),
            offending_object_ids=offending,
        )


def validate_whole_tree(
    document: Any,
    stage3_expected_ids: set[str],
) -> None:
    all_objects = _iter_all_objects(document)

    _check_invariant_1(document)
    _check_invariant_2(document, all_objects)
    _check_invariant_3(document, all_objects)
    _check_invariant_4(document)
    _check_invariant_5(all_objects)
    _check_invariant_6(document)
    _check_invariant_7(document)
    _check_invariant_8(document, all_objects, stage3_expected_ids)

    logger.debug("stage11 complete: all 8 whole-tree invariants passed")