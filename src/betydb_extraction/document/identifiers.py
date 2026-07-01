from __future__ import annotations

import hashlib
import re

__all__ = [
    "DOCUMENT_ID_PREFIX",
    "OBJECT_ID_PREFIX",
    "compute_document_id",
    "compute_object_id",
    "is_valid_document_id",
    "is_valid_object_id",
    "validate_document_id_shape",
    "validate_object_id_shape",
]

DOCUMENT_ID_PREFIX = "betydoc:"
OBJECT_ID_PREFIX = "doc:"

_HASH_TRUNCATION_LENGTH = 16

# An identifier is the literal prefix followed by exactly 16 lowercase
# hexadecimal characters, per the truncation length used by both
# compute_document_id and compute_object_id below.
_DOCUMENT_ID_PATTERN = re.compile(
    rf"^{re.escape(DOCUMENT_ID_PREFIX)}[0-9a-f]{{{_HASH_TRUNCATION_LENGTH}}}$"
)
_OBJECT_ID_PATTERN = re.compile(
    rf"^{re.escape(OBJECT_ID_PREFIX)}[0-9a-f]{{{_HASH_TRUNCATION_LENGTH}}}$"
)


def compute_document_id(source_pdf_identifier: str) -> str:
    digest = hashlib.sha256(source_pdf_identifier.encode("utf-8")).hexdigest()
    return DOCUMENT_ID_PREFIX + digest[:_HASH_TRUNCATION_LENGTH]


def compute_object_id(document_id: str, canonical_path: str) -> str:
    payload = f"{document_id}|{canonical_path}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return OBJECT_ID_PREFIX + digest[:_HASH_TRUNCATION_LENGTH]


def is_valid_document_id(value: str) -> bool:
    return bool(_DOCUMENT_ID_PATTERN.match(value))


def is_valid_object_id(value: str) -> bool:
    return bool(_OBJECT_ID_PATTERN.match(value))


def validate_document_id_shape(value: str) -> str:
    if not is_valid_document_id(value):
        raise ValueError(
            f"{value!r} is not a valid Document id "
            f"(expected '{DOCUMENT_ID_PREFIX}' + "
            f"{_HASH_TRUNCATION_LENGTH} lowercase hex characters)"
        )
    return value


def validate_object_id_shape(value: str) -> str:
    if not is_valid_object_id(value):
        raise ValueError(
            f"{value!r} is not a valid object id "
            f"(expected '{OBJECT_ID_PREFIX}' + "
            f"{_HASH_TRUNCATION_LENGTH} lowercase hex characters)"
        )
    return value