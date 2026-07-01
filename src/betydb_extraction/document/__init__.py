from __future__ import annotations

from betydb_extraction.document.caption import Caption
from betydb_extraction.document.document import Document
from betydb_extraction.document.enums import NodeKind
from betydb_extraction.document.equation import Equation
from betydb_extraction.document.figure import Figure
from betydb_extraction.document.footnote import Footnote
from betydb_extraction.document.identifiers import (
    DOCUMENT_ID_PREFIX,
    OBJECT_ID_PREFIX,
    compute_document_id,
    compute_object_id,
    is_valid_document_id,
    is_valid_object_id,
    validate_document_id_shape,
    validate_object_id_shape,
)
from betydb_extraction.document.metadata import Metadata
from betydb_extraction.document.page import Page, PageChild
from betydb_extraction.document.page_furniture import PageFooter, PageHeader
from betydb_extraction.document.paragraph import Paragraph
from betydb_extraction.document.processing_metadata import ProcessingMetadata
from betydb_extraction.document.provenance import (
    BoundingBox,
    Polygon,
    StructuralProvenance,
)
from betydb_extraction.document.reference import Reference
from betydb_extraction.document.section import Section, SectionChild
from betydb_extraction.document.statistics import Statistics
from betydb_extraction.document.table import Table, TableCell, TableRow, TableRowCell

__all__ = [
    "BoundingBox",
    "Caption",
    "DOCUMENT_ID_PREFIX",
    "Document",
    "Equation",
    "Figure",
    "Footnote",
    "Metadata",
    "NodeKind",
    "OBJECT_ID_PREFIX",
    "Page",
    "PageChild",
    "PageFooter",
    "PageHeader",
    "Paragraph",
    "Polygon",
    "ProcessingMetadata",
    "Reference",
    "Section",
    "SectionChild",
    "Statistics",
    "StructuralProvenance",
    "Table",
    "TableCell",
    "TableRow",
    "TableRowCell",
    "compute_document_id",
    "compute_object_id",
    "is_valid_document_id",
    "is_valid_object_id",
    "validate_document_id_shape",
    "validate_object_id_shape",
]

# Resolve forward references for the recursive Section <-> SectionChild
# union and the Page -> Section dependency, in dependency order. 
Page.model_rebuild()
Document.model_rebuild()