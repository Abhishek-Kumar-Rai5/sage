"""Text-key construction helpers and uniqueness checks.

Implements IR Specification Section 4 ("Identifier Strategy").
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = ["check_ids_unique", "validate_text_key_shape"]

_TEXT_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def validate_text_key_shape(value: str) -> str:
    if not _TEXT_KEY_PATTERN.match(value):
        raise ValueError(
            f"{value!r} is not a valid IR text key (expected lowercase "
            "alphanumeric segments separated by underscores)."
        )
    return value


def check_ids_unique(ids: Iterable[str], *, entity_name: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for entity_id in ids:
        if entity_id in seen:
            duplicates.add(entity_id)
        seen.add(entity_id)
    if duplicates:
        raise ValueError(
            f"Duplicate {entity_name} id(s) found: {sorted(duplicates)}."
        )