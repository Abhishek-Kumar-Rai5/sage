from __future__ import annotations

from enum import Enum

__all__ = ["ProvenanceLabel"]


class ProvenanceLabel(str, Enum):
    """Provenance state of a field-level value.

    IR Spec Section 5, Table 3. Adopted verbatim from the parent project
    proposal: "every field labeled as extracted, inferred or unresolved."
    """

    EXTRACTED = "extracted"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"