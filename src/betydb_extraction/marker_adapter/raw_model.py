from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MarkerPolygonPoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    x: float
    y: float

    @classmethod
    def from_pair(cls, pair: "list[float] | tuple[float, float]") -> "MarkerPolygonPoint":
        """Construct from Marker's raw ``[x, y]`` list/tuple representation."""
        x, y = pair
        return cls(x=x, y=y)

    def to_pair(self) -> list[float]:
        """Serialize back to Marker's raw ``[x, y]`` list representation."""
        return [self.x, self.y]


class MarkerBBox(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_list(cls, values: "list[float]") -> "MarkerBBox":
        """Construct from Marker's raw ``[x0, y0, x1, y1]`` list representation."""
        x0, y0, x1, y1 = values
        return cls(x0=x0, y0=y0, x1=x1, y1=y1)

    def to_list(self) -> list[float]:
        """Serialize back to Marker's raw ``[x0, y0, x1, y1]`` list representation."""
        return [self.x0, self.y0, self.x1, self.y1]


class MarkerBlock(BaseModel):

    model_config = ConfigDict(
        frozen=True,
        # Marker's schema may evolve. Unknown fields are preserved rather
        # than silently dropped, so that upgrading Marker never causes
        # silent data loss even before this model is updated to formally
        # recognize a new field. See module docstring, point 4.
        extra="allow",
    )

    id: Optional[str] = Field(
        default=None,
        description=(
            "Marker's own block identifier, e.g. '/page/7/Table/2'. This is "
            "a path-like string encoding page index, block_type, and a "
            "local positional index. It is preserved verbatim and is NOT "
            "guaranteed to be globally stable across different Marker "
            "versions or runs -- treat it as provenance to the specific "
            "Marker invocation that produced this tree, not as a permanent "
            "cross-run identifier. Permanent identifiers are derived later, "
            "in the Document Object layer. Modeled as Optional because the "
            "root 'Document' block in observed Marker output omits this "
            "field entirely (along with html, polygon, bbox, and "
            "section_hierarchy) -- it is structurally a bare wrapper "
            "around the page children and carries no positional identity "
            "of its own."
        ),
    )

    block_type: str = Field(
        ...,
        description=(
            "Marker's block type tag, e.g. 'Page', 'Table', 'TableCell', "
            "'Text', 'SectionHeader', 'Footnote', 'Caption', 'Figure', "
            "'FigureGroup', 'TableGroup', 'Picture', 'ListGroup', "
            "'ListItem', 'PageHeader', 'PageFooter', 'Equation', "
            "'Document'. Modeled as a plain ``str`` rather than an ``Enum`` "
            "or discriminator so that an unrecognized block_type from a "
            "future Marker version still parses successfully."
        ),
    )

    html: str = Field(
        default="",
        description=(
            "For leaf blocks: the actual inline HTML content of this block "
            "(e.g. '<p block-type=\"Text\">...</p>'). For container blocks: "
            "a manifest of '<content-ref src=\"...\"></content-ref>' "
            "pointers to this block's children, in reading order -- in "
            "that case this field is redundant with `children` and should "
            "be treated as a reading-order hint only, not primary content. "
            "Distinguishing these two cases is a Normalizer responsibility "
            "(in practice: `children is None` implies the html is real "
            "leaf content; `children is not None` implies it is a "
            "content-ref manifest), not something this model decides."
        ),
    )

    polygon: Optional[list[MarkerPolygonPoint]] = Field(
        default=None,
        description=(
            "The block's bounding polygon as a list of corner points, in "
            "Marker's native page coordinate space. Observed in practice as "
            "4 points (a rectangle) but modeled as a list of arbitrary "
            "length since Marker's polygon format is not contractually "
            "limited to 4 points."
        ),
    )

    bbox: Optional[MarkerBBox] = Field(
        default=None,
        description=(
            "The block's axis-aligned bounding box [x0, y0, x1, y1] in "
            "Marker's native page coordinate space."
        ),
    )

    children: Optional[list["MarkerBlock"]] = Field(
        default=None,
        description=(
            "Nested child blocks, in reading order, or `None` for a true "
            "leaf block. `None` and `[]` are deliberately NOT collapsed "
            "into one representation -- in observed Marker output, leaf "
            "blocks have `children: None`, never `children: []`; preserving "
            "this distinction exactly as Marker emits it is part of this "
            "layer's lossless mandate."
        ),
    )

    section_hierarchy: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "A mapping from depth-index string (e.g. '1', '4') to the "
            "Marker block id of the governing SectionHeader at that depth, "
            "as emitted by Marker for this specific block. This is a live "
            "breadcrumb of the heading path above this block at the time "
            "Marker produced the tree."
        ),
    )

    images: Optional[dict[str, str]] = Field(
        default=None,
        description=(
            "A mapping from (typically this block's own) Marker id to a "
            "base64-encoded image payload. Populated for blocks that embed "
            "raster image data (observed: 'Picture' blocks); `{}` for the "
            "large majority of blocks that carry no image data. Modeled as "
            "Optional rather than defaulting to `{}` because Marker's own "
            "output for this field was observed to vary between `{}` and "
            "(for Page-level container blocks) `None` is not ruled out by "
            "the schema even though `{}` was the only empty case directly "
            "observed in this paper's output -- see point 3 in the module "
            "docstring on not collapsing absent vs. empty."
        ),
    )

    @field_validator("polygon", mode="before")
    @classmethod
    def _coerce_polygon(cls, value: Any) -> Any:
        if value is None:
            return value
        coerced = []
        for point in value:
            if isinstance(point, MarkerPolygonPoint):
                coerced.append(point)
            elif isinstance(point, dict):
                coerced.append(point)
            else:
                # Raw [x, y] list/tuple as emitted by Marker.
                coerced.append(MarkerPolygonPoint.from_pair(point))
        return coerced

    @field_validator("bbox", mode="before")
    @classmethod
    def _coerce_bbox(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, MarkerBBox) or isinstance(value, dict):
            return value
        return MarkerBBox.from_list(value)

    def is_leaf(self) -> bool:
        return self.children is None

    def iter_descendants(self) -> "list[MarkerBlock]":
        result: list[MarkerBlock] = []
        for child in self.children or []:
            result.append(child)
            result.extend(child.iter_descendants())
        return result


class MarkerDocument(BaseModel):

    model_config = ConfigDict(frozen=True, extra="allow")

    root: MarkerBlock = Field(
        ...,
        description=(
            "The root block of Marker's output tree for this document "
            "(observed block_type: 'Document')."
        ),
    )

    source_marker_json_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional filesystem path or identifier of the raw Marker JSON "
            "file this object was parsed from, retained purely for "
            "debugging and provenance traceability. Not part of Marker's "
            "own output -- populated by the adapter at parse time."
        ),
    )

    @property
    def pages(self) -> list[MarkerBlock]:
        return self.root.children or []
