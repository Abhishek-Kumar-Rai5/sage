"""IRDataset builder factory.
"""

from __future__ import annotations

from betydb_extraction.document.document import Document
from betydb_extraction.ir.dataset import IRDataset

__all__ = ["build_ir_dataset"]


def build_ir_dataset(document: Document, *, dataset_id: str) -> IRDataset:
    raise NotImplementedError(
        "build_ir_dataset extraction logic is out of scope for Week 2. "
        "This stub defines the factory interface only; the metadata-first "
        "extraction chain (Technical Work Plan Section 2.2) is implemented "
        "in a later phase."
    )