from __future__ import annotations

from enum import Enum

__all__ = ["NodeKind"]


class NodeKind(str, Enum):

    SECTION = "section"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    EQUATION = "equation"
    FOOTNOTE = "footnote"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"
    REFERENCE = "reference"