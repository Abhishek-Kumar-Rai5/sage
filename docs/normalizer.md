# Normalizer Design Specification

**Layer:** Document Understanding Layer (Normalizer)
**Version:** 1.1
**Status:** Approved — implementation contract
**Upstream contract:** Raw Marker Model (`marker_adapter/raw_model.py`), frozen
**Downstream contract:** Document Schema Specification v1.1, frozen
**Empirical basis:** Marker Output — Empirical Findings (Paper 1: Nutrient Cycling,
Smukler et al. 2012), plus the empirical evaluation referenced across three
representative papers

This is an engineering specification, not implementation. It defines what the
Normalizer must do, in what order, under what invariants, and where its
responsibility ends — so that implementing it in Python becomes translation, not
design. No code is written here.

---

## Revision Record

**Version 1.1 (current, approved).** Resolves the following issues identified
during the implementation-readiness audit of v1.0. Each issue is identified by
the audit code; the correction applied is described at its point of change and
summarised here.

- **CRITICAL-1** (ungoverned content and top-level `Section` interleaving order in
  `PageBuilder.children` unspecified): resolved in §5 Stage 7 by stating
  explicitly that all items placed into `PageBuilder.children` — ungoverned leaf
  builders and top-level `SectionBuilder`s alike — are inserted in the order their
  originating block first appears in the page's Stage-2 flat classified sequence,
  via a single forward pass.
- **CRITICAL-2** (Stage 7 step 5's `SectionBuilder` nesting algorithm assumed
  `SectionHeader` blocks carry their own `section_hierarchy` field, which is not
  confirmed): resolved in §5 Stage 7 by replacing the forward-path assumption with
  a confirmed reverse-lookup algorithm: a `SectionBuilder`'s depth and parent
  section are determined by finding where its heading block's Marker id appears in
  the `section_hierarchy` dicts of the content blocks it governs.
- **CRITICAL-3** (`kind` discriminator field required by Schema v1.1's discriminated
  union never assigned in any stage): resolved in §5 Stage 3 and Appendix A by
  adding a blanket rule that each builder's `kind` field is set at Stage 3
  construction to the fixed string literal required by Schema v1.1 for that object
  type.
- **CRITICAL-4** (Stage 2's `CAPTION_LABEL` override condition required lookahead
  into not-yet-classified blocks by referencing their `disposition` values, which do
  not exist at classification time): resolved in §5 Stage 2 by replacing the
  disposition-based lookahead with a `block_type`-based lookahead — the unwrapped
  sequence's `block_type` fields are available before classification runs.
- **MAJOR-1** (Stage 0 signal S4 referenced "the section-heading vocabulary defined
  in Stage 2," which Stage 2 does not define as a general vocabulary): resolved in
  §5 Stage 0 by redefining S4 as a structural check — any block whose `block_type`
  is `SectionHeader` present on the page, with no vocabulary list required.
- **MAJOR-2** (builder field lists were illustrative examples for `PageBuilder` only;
  other builder types had no complete definition): resolved in §4.1 by adding a
  blanket rule covering all builder types uniformly.
- **MAJOR-3** (§24 missing a whole-tree invariant verifying that every Stage-3
  object builder appears exactly once in the final materialized tree): resolved in
  §24 by adding invariant 8.
- **MAJOR-4** (Stage 5 gave no rule for the `cells` list of a bare `Table` block
  with `wrapper_context = None`): resolved in §5 Stage 5 by stating explicitly that
  bare tables have `cells = []`.
- **MAJOR-5** (Stage 6 tie-break unspecified when two candidates share the same
  maximum `bbox.y1`): resolved in §5 Stage 6 by specifying page-array index as the
  tie-break.
- **MAJOR-6** (Stage 10 step 7 said "`SectionBuilder`s, innermost-first" without
  specifying the traversal algorithm for arbitrary nesting depth): resolved in §5
  Stage 10 by naming post-order depth-first traversal explicitly.
- **MAJOR-7** (`ProcessingMetadata` construction absent from Stage 10's numbered
  steps): resolved in §5 Stage 10 by adding step 9.
- **MAJOR-8** (`Document` root constructor call never specified in any stage):
  resolved in §5 Stage 10 by adding step 10.

**Version 1.0.** Resolved all issues from the v1.0-draft freeze review (CRITICAL-1
through CRITICAL-2, MAJOR-1 through MAJOR-10, MINOR-1 through MINOR-8 of that
review). See v1.0 revision record for details.

---

## 1. Overall Responsibility and Scope

The Normalizer is the single component permitted to transform a `MarkerDocument`
(Raw Marker Model) into a `Document` (Document Object, per Schema v1.1). It is a
pure function in spirit, if not literally in implementation: given the same
`MarkerDocument` and the same `source_pdf_identifier`, it always produces a
byte-identical `Document`.

Its responsibility is exactly the set of decisions Schema v1.1 explicitly delegates
to "Normalizer business logic" — every place the schema says "this is a Normalizer
concern" is a place this specification must give a concrete, ordered rule. The
Normalizer's job is:

- Unwrapping Marker's three wrapper block types (`TableGroup`, `FigureGroup`,
  `ListGroup`) from the raw children array before any classification occurs.
- Deciding which Marker blocks become which Document Object types (the
  `block_type` → disposition mapping).
- Resolving the two confirmed caption patterns (Pattern A: `TableGroup`/`FigureGroup`
  wrapper; Pattern B: bare `CAPTION_LABEL` + `Text` + object + optional trailing
  `Text`) into one normalized `Caption` per finding 3.1.
- Resolving footnote-to-table/figure attachment via bbox-proximity geometry,
  per finding 3.2.
- Distinguishing genuine paper `Section`s from `SectionHeader` blocks that are
  actually caption labels, per Schema v1.1 §9.
- Distinguishing body-text `Paragraph`s from bibliography `Reference`s when both
  arrive as Marker `ListItem` blocks, per Schema v1.1 §10/§16.
- Computing every deterministic `id` per Schema v1.1 §2.
- Computing global `reading_order_index` values from final tree position, per
  Schema v1.1 §3.4.
- Detecting front-matter pages heuristically (`Page.is_front_matter`), per
  Schema v1.1 §8.
- Parsing `Table.raw_html` into `TableRow`/`TableRowCell` structure, per Schema
  v1.1 §§12.1–12.2.
- Assembling `Statistics`, `Metadata`, and `ProcessingMetadata` as a final derived
  pass over the completed tree.

What the Normalizer never does: it never recognizes a species, treatment,
management event, variable, or any scientific concept; it never maps anything to a
BETYdb field or ontology term; it never parses a citation into author/year/journal;
it never assigns a confidence score to a scientific claim. Every one of those is
explicitly out of scope per Schema v1.1 invariant 1.2.

---

## 2. Inputs and Outputs

**Inputs (exactly three, all required):**

1. `marker_document: MarkerDocument` — the parsed Raw Marker Model for one PDF,
   already validated and immutable.
2. `source_pdf_identifier: str` — the stable external identifier for the source
   PDF (DOI if known, else a content hash of the source PDF bytes), per Schema
   v1.1 §2's `document_id` construction. The Normalizer does not compute this
   itself — it is supplied by the caller.
3. `processing_context: NormalizerProcessingContext` — a small explicit value
   bundle defined as follows:

```python
@dataclass(frozen=True)
class NormalizerProcessingContext:
    marker_version: str         # Version string of the Marker run that produced
                                # the MarkerDocument. Verbatim into
                                # ProcessingMetadata.marker_version.
    normalizer_version: str     # Semantic version of this Normalizer code.
                                # Verbatim into ProcessingMetadata.normalizer_version.
    source_marker_artifact_ref: str  # Path or content hash identifying the Raw
                                     # Marker Model JSON file this Document Object
                                     # is derived from. Verbatim into
                                     # ProcessingMetadata.source_marker_artifact_ref.
    processed_at: datetime      # Wall-clock UTC datetime of this materialization.
                                # Must be timezone-aware UTC. Verbatim into
                                # ProcessingMetadata.processed_at.
```

   These map directly onto `ProcessingMetadata` (Schema v1.1 §6) but are supplied
   explicitly rather than invented internally, since "what Marker version was run"
   and "what artifact file is this" are facts about the calling environment that the
   Normalizer cannot derive from the `MarkerDocument` tree alone — the empirical
   findings confirmed the Raw Marker root block carries no version metadata field.

**Output (exactly one):** `document: Document` — a fully constructed, valid Schema
v1.1 `Document` object, or the Normalizer raises (see §22) without returning a
partially-built object. There is no "best effort, partially populated" return mode.

**Non-goals of the output:** the returned `Document` is not written to disk,
not serialized, not logged. Persistence and serialization are caller responsibilities.

---

## 3. Public API

```python
def normalize(
    marker_document: MarkerDocument,
    source_pdf_identifier: str,
    processing_context: NormalizerProcessingContext,
) -> Document:
    ...
```

This is the only public entry point. Everything else (per-object builder functions,
the bbox-proximity matcher, the caption-pattern resolver, the unwrapper) is an
internal implementation detail of the `normalizer` package and must not be imported
or relied upon by any other layer.

A single narrow exception is permitted for testability: the internal stage
functions may be exposed as a separate, explicitly-not-public module
(e.g. `normalizer._internal`) so that unit tests can exercise individual stages in
isolation without requiring a full `MarkerDocument` fixture for every test. This
does not change the public contract — `normalize()` remains the only function any
other layer may call.

---

## 4. Internal Architecture

### 4.1 The Builder Pattern

Schema v1.1 declares all Document Object models as `frozen=True`. A frozen Pydantic
model cannot have any field mutated after construction. The pipeline requires
populating different fields of the same logical object at different stages.
These two facts are reconciled by a single architectural decision: **the Normalizer
never constructs a frozen Schema v1.1 model until all of that model's fields are
finalized.**

During pipeline execution (Stages 0–9), the Normalizer works exclusively with
**mutable builder objects** — plain Python `dataclass` instances, one per Schema
v1.1 model type — that accumulate field values across stages. At **Stage 10
(Materialization)**, each builder is converted to its corresponding frozen Schema
v1.1 model exactly once, in a single bottom-up pass. No frozen Schema v1.1 model
exists at any point before Stage 10.

**Complete builder field rule (resolves MAJOR-2):** Every builder type — without
exception — is defined as a Python `dataclass` containing exactly the fields of its
corresponding Schema v1.1 model, all typed `Optional` and defaulting to `None`,
plus one additional field not present in Schema v1.1: `canonical_path: str | None
= None`, which is populated by Stage 9 and consumed by Stage 10 to compute `id`.
No other fields are added to any builder. This rule is stated here once and applies
to every builder type named anywhere in this specification; individual stage
descriptions do not re-state it.

**`kind` field rule (resolves CRITICAL-3):** Schema v1.1 uses a discriminated
union for `Page.children` and `Section.children`, requiring a `kind` literal field
on every union member. Each builder's `kind` field is set at construction time in
Stage 3 (or Stage 4 for `CaptionBuilder`) to the fixed string literal required by
Schema v1.1 for that object type, and is carried through to Stage 10 unchanged.
`kind` is never left `None` on any builder after Stage 3. The complete mapping is
determined by Schema v1.1's own discriminated union declarations and is not
reproduced here — the mapping is a read-once-from-schema value, not a design
decision.

The builder types mirror the Schema v1.1 models field-for-field, but with all
fields typed as `Optional` and defaulting to `None`, and with no `frozen=True`:

```python
# Example — illustrative only; every Schema v1.1 model type has a corresponding
# builder following the complete builder field rule above.
@dataclass
class PageBuilder:
    kind: str | None = None             # Set at Stage 3; Schema v1.1 literal value
    page_number: int | None = None
    is_front_matter: bool | None = None
    provenance: ProvenanceBuilder | None = None
    children: list[Any] = field(default_factory=list)
    canonical_path: str | None = None   # Added field; Stage 9 only

@dataclass
class ProvenanceBuilder:
    marker_block_ids: list[str] = field(default_factory=list)
    page_number: int | None = None
    bbox: BoundingBox | None = None
    contributing_bboxes: list[BoundingBox] | None = None
    polygon: Polygon | None = None
    reading_order_index: int | None = None
    section_path: list[str] = field(default_factory=list)
```

`BoundingBox` and `Polygon` are constructed directly from Marker geometry data at
the stage where that geometry is first processed — they are leaf value types with no
fields that depend on later stages, so constructing them immediately is correct and
safe. All other frozen Schema v1.1 models are deferred to Stage 10.

Stage 10 is named **Materialization** in this specification to make clear that its
primary role is the builder-to-model conversion pass. Metadata, Statistics, and
ProcessingMetadata assembly remain part of Stage 10 but are secondary to
materialization.

### 4.2 Wrapper Unwrapping

Marker's output contains three wrapper block types that bundle related children
under a common parent: `TableGroup` (wraps `[Caption, Table]`), `FigureGroup`
(wraps `[Figure, Caption]` — reversed order relative to `TableGroup`, confirmed
empirically), and `ListGroup` (wraps `[ListItem, ...]`). These wrappers exist in
Marker's tree but have no corresponding Document Object type in Schema v1.1. Stage
2 cannot classify their children as siblings alongside other blocks unless the
wrappers are first removed.

**Resolution:** A new **Stage 1.5 (Wrapper Unwrapping)** runs immediately after
Stage 1 and before Stage 2. Its sole job is to produce a flat, ordered sequence of
`(MarkerBlock, wrapper_context)` pairs from each page's raw `children` array, where
`wrapper_context` records the parent wrapper block's id and type for any block that
was inside a wrapper, and is `None` for blocks that were direct page children. Stage
2 and all subsequent stages work exclusively against this unwrapped sequence, never
against the original nested tree.

The complete unwrapping rule is:

- A `TableGroup` block is replaced in the sequence by its children in original
  order, each tagged with
  `wrapper_context = WrapperContext(wrapper_type="TableGroup", block_id=<id>)`.
- A `FigureGroup` block is replaced in the sequence by its children in original
  order, each tagged with
  `wrapper_context = WrapperContext(wrapper_type="FigureGroup", block_id=<id>)`.
- A `ListGroup` block is replaced in the sequence by its children in original
  order, each tagged with
  `wrapper_context = WrapperContext(wrapper_type="ListGroup", block_id=<id>)`.
- Any other block type is placed into the sequence unchanged with
  `wrapper_context = None`.
- Unwrapping is exactly one level deep. If a wrapper contains a nested wrapper
  (not observed empirically but structurally possible in Marker), the inner wrapper
  is NOT recursively unwrapped — it is placed into the sequence as an ordinary
  block, and Stage 2's `UnrecognizedBlockTypeError` path (§22) handles it if it is
  not a recognized non-wrapper block type. This is a deliberately conservative
  rule: if nested wrappers appear in a future paper, the failure is loud, not
  silent.

After Stage 1.5, every subsequent stage sees only a flat, ordered
`list[UnwrappedBlock]` per page:

```python
@dataclass(frozen=True)
class WrapperContext:
    wrapper_type: str   # "TableGroup" | "FigureGroup" | "ListGroup"
    block_id: str       # The wrapper block's own Marker id

@dataclass(frozen=True)
class UnwrappedBlock:
    block: MarkerBlock
    wrapper_context: WrapperContext | None
```

Stage 4 (Caption resolution) uses `wrapper_context` to determine which pattern
applies: a `Table` or `Figure` block with `wrapper_context.wrapper_type in
{"TableGroup", "FigureGroup"}` is Pattern A; one with `wrapper_context = None` is
Pattern B. The original wrapper block id is included in provenance (as an additional
entry in `marker_block_ids`) when Pattern A applies, per Schema v1.1 §12/§13.

### 4.3 Stage Sequence

```
MarkerDocument
      │
      ▼
[Stage 0]   Front-matter detection (per page, produces is_front_matter flags)
      │
      ▼
[Stage 1]   Page builder construction (PageBuilder shells, one per page)
      │
      ▼
[Stage 1.5] Wrapper unwrapping (produces flat UnwrappedBlock sequences per page)
      │
      ▼
[Stage 2]   Block classification (UnwrappedBlock → disposition tag per block)
      │
      ▼
[Stage 3]   Leaf builder construction (all object builders except id,
            reading_order_index, section_path, caption, rows/cells,
            footnote linkage — those come from later stages)
      │
      ▼
[Stage 4]   Caption resolution (Table/Figure builders gain caption builders)
      │
      ▼
[Stage 5]   Table internal structure (raw_html → TableRow/TableRowCell builders;
            flat TableCell builders from Marker TableCell children)
      │
      ▼
[Stage 6]   Footnote attachment (bbox-proximity → footnote_ids / attached_object_id
            on builder objects, both sides set atomically)
      │
      ▼
[Stage 7]   Section tree assembly (flat builders + section_hierarchy breadcrumbs
            → nested SectionBuilder tree; section_path on each builder populated)
      │
      ▼
[Stage 8]   Global reading-order assignment (depth-first traversal of builder tree
            → reading_order_index on every ProvenanceBuilder)
      │
      ▼
[Stage 9]   Canonical path computation (every builder's canonical_path computed;
            used by Stage 10 to compute ids)
      │
      ▼
[Stage 10]  Materialization (builders → frozen Schema v1.1 models, bottom-up;
            id computed per Schema v1.1 §2 during this pass;
            Metadata, Statistics, and ProcessingMetadata assembled;
            Document root object constructed)
      │
      ▼
[Stage 11]  Whole-tree validation (cross-object invariants, §24)
      │
      ▼
Document
```

**Why Stage 9 (canonical path computation) precedes Stage 10 (materialization)
rather than being merged into it.** Stage 10 materializes objects bottom-up,
meaning a leaf object's frozen model is constructed before its parent's. A leaf's
`canonical_path` (and therefore its `id`) depends only on its own position in the
final tree, not on its parent's id — Schema v1.1 §2's hash rule is
`sha256(document_id + "|" + canonical_path)`, and `document_id` is computed once
at the start of Stage 10 from `source_pdf_identifier`. So `id` computation is
mechanical once `canonical_path` is known. Stage 9 computes and stores
`canonical_path` as a field on each builder, so Stage 10 can compute each object's
`id` during its own bottom-up pass without needing to traverse the tree again.

**Why reading-order (Stage 8) precedes canonical-path (Stage 9).** Some synthesized
objects (e.g. a `TableRow` with no direct 1:1 Marker block) have a `canonical_path`
that incorporates their ordinal position among siblings. `reading_order_index` is
the only ordering that is both deterministic and tree-position-derived for such
objects. Computing reading order before canonical paths ensures synthesized-object
paths are stable.

The Stage 0–11 sequence is a hard contract. No stage may be reordered without a
reviewed revision of this specification.

---

## 5. Processing Pipeline — Stage-by-Stage Detail

### Stage 0: Front-matter detection

**Input:** each page's `MarkerBlock` from `marker_document.children` (the top-level
page blocks).
**Output:** a `dict[int, bool]` mapping page index → `is_front_matter`, consumed by
Stage 1.

Per Schema v1.1 §8 and finding 3.8, Marker gives no structural signal distinguishing
a publisher wrapper page from a content page. Detection is a content-pattern
heuristic applied to the concatenated plain text of all `Text`-typed blocks on the
page. The following signals are checked:

| Signal | Type | Pattern |
|--------|------|---------|
| S1 | Fixed string (case-sensitive) | `"Submit your article"` |
| S2 | Regex | `r"\bISSN\s*[\d\-]{4,10}"` |
| S3 | Regex | `r"Article views:\s*\d+"` |
| S4 | Structural | No block with `block_type == "SectionHeader"` is present anywhere in the page's raw `children` array (before unwrapping). |

**S4 correction (resolves MAJOR-1):** S4 was previously defined as checking
against "the section-heading vocabulary defined in Stage 2," which Stage 2 does not
define as a general vocabulary. S4 is now a purely structural check — the presence
or absence of any `SectionHeader`-typed block on the page, requiring no vocabulary
list. S4 fires (contributes toward the two-signal threshold) when no
`SectionHeader` block exists on the page at all. This check runs against the raw
`children` array, before Stage 1.5 unwrapping, because it is a property of the
page's block-type composition, not of classified dispositions.

A page is flagged `is_front_matter = True` if and only if **at least two** of S1,
S2, S3, S4 fire. S4 alone is not sufficient. No signal beyond these four is
introduced speculatively — additional signals require a new representative paper
to confirm.

This stage produces only the boolean flags; it does not alter, skip, or omit
processing of any page's content in any later stage.

### Stage 1: Page builder construction

**Input:** `marker_document.children` (the list of top-level page blocks), Stage 0
flags.
**Output:** a list of `PageBuilder` instances, one per page, with `page_number` and
`is_front_matter` set; `provenance.marker_block_ids = [page_block.id]`;
`provenance.bbox` set from `page_block.bbox` if present; `children` empty.

Page numbering is taken from the block's position in `marker_document.children`
(0-indexed array position), not parsed from the Marker block's `id` string.

Note on the Raw Marker Model root: the Marker root node (`MarkerDocument`) was
empirically confirmed to have no `id`, `bbox`, or `polygon` of its own. `Document`
therefore has no `StructuralProvenance` (Schema v1.1 §4). Stage 1 does not attempt
to construct provenance for the `Document` itself.

### Stage 1.5: Wrapper unwrapping

**Input:** each page's raw Marker `children` array.
**Output:** per page, a `list[UnwrappedBlock]` as defined in §4.2.

Unwrapping is exactly one level deep and covers exactly `TableGroup`, `FigureGroup`,
and `ListGroup` block types. All three wrapper types are unwrapped
unconditionally — there is no precondition check. The `wrapper_context` field on
each extracted child records the wrapper's type and block id for use by Stage 4.

Any block type not listed above that appears in the original children array is
placed into the unwrapped sequence unchanged with `wrapper_context = None`,
regardless of whether it itself has children — Stage 1.5 is a single-level
operation only.

The original Marker `children` array is preserved unmodified (it is part of the
immutable `MarkerDocument`) — Stage 1.5 produces a separate derived sequence and
does not alter the input.

### Stage 2: Block classification

**Input:** each page's `list[UnwrappedBlock]` from Stage 1.5.
**Output:** a `list[ClassifiedBlock]` per page.

```python
@dataclass(frozen=True)
class ClassifiedBlock:
    unwrapped: UnwrappedBlock
    disposition: Disposition
```

**Complete disposition enum** (all block types confirmed present in the Raw Marker
Model are covered; `UnrecognizedBlockTypeError` fires only for block types not in
this table):

| Marker `block_type` | Default disposition | Override conditions |
|---------------------|--------------------|--------------------|
| `SectionHeader` | `GENUINE_SECTION_HEADER` | → `CAPTION_LABEL` if both: (a) text matches `^(Table\|Figure)\s+\d+[\.:]?\s*$` (case-insensitive), AND (b) within the next three blocks in the unwrapped sequence, a block whose **`block_type`** is `"Table"` or `"Figure"` exists. |
| `Text` | `BODY_PARAGRAPH` | — |
| `Table` | `TABLE_SHELL` | — |
| `Figure` | `FIGURE_SHELL` | — |
| `Caption` | `CAPTION_TEXT` | Only appears inside a `TableGroup`/`FigureGroup` wrapper |
| `TableCell` | `TABLE_CELL_EVIDENCE` | Only appears as a sibling of `Table` inside a `TableGroup` |
| `Equation` | `EQUATION` | — |
| `Footnote` | `FOOTNOTE` | — |
| `PageHeader` | `PAGE_HEADER` | — |
| `PageFooter` | `PAGE_FOOTER` | — |
| `ListItem` | `BODY_PARAGRAPH` | → `REFERENCE_ENTRY` if governing section heading text matches the references-heading vocabulary (see below) |
| `Picture` | `PICTURE` | Dropped — no builder constructed; log entry produced (§23) |

**CAPTION_LABEL override lookahead (resolves CRITICAL-4):** The override condition
checks whether "within the next three blocks in the unwrapped sequence, a block
whose `block_type` is `"Table"` or `"Figure"` exists." This uses the raw
`block_type` field of the `UnwrappedBlock.block`, not the block's `disposition` —
`disposition` values for subsequent blocks are not yet assigned when this
`SectionHeader` is being classified. Using `block_type` directly is correct and
unambiguous because Stage 1.5 has already unwrapped all wrapper containers, so any
`Table` or `Figure` block in the flat sequence is visible with its literal
`block_type` value. The three-block window accommodates Pattern B's confirmed
structure (CAPTION_LABEL block, then a Text block, then the Table/Figure block —
two intervening blocks at most, with one block of margin).

**`ListItem` → `REFERENCE_ENTRY` rule:** a `ListItem`'s governing section is
determined by taking its originating Marker block's `section_hierarchy` field,
sorting the depth-key strings numerically, and resolving the deepest entry to its
corresponding `GENUINE_SECTION_HEADER`-classified block (already determined in this
same Stage 2 pass, processing blocks in array order so that all headings before this
`ListItem` in reading order have already been classified). The references-heading
vocabulary is a fixed list: `{"references", "bibliography", "works cited",
"literature cited"}` (all compared case-insensitively). A `ListItem` whose deepest
governing section heading does not match this vocabulary, or which has no governing
section at all, is classified `BODY_PARAGRAPH`.

**Adjacency transparency for `PICTURE` blocks:** `PICTURE`-classified blocks are
ignored when evaluating the Pattern B adjacency checks in Stage 4. They are present
in the classified sequence but treated as transparent — their positions do not count
toward "immediately preceding" or "immediately following" relationships. This rule
applies only to Stage 4's adjacency scan; all other stage passes treat
`PICTURE`-classified blocks as ordinary (non-builder-producing) entries.

### Stage 3: Leaf builder construction

**Input:** `list[ClassifiedBlock]` per page from Stage 2.
**Output:** per page, a flat `list[ObjectBuilder]` — one builder per classified
block that maps to a Document Object (see exclusions below), with all directly
available fields populated.

**`kind` field assignment (resolves CRITICAL-3):** Every builder constructed in
Stage 3 has its `kind` field set immediately at construction to the fixed string
literal required by Schema v1.1's discriminated union for that object type. `kind`
is never `None` after Stage 3. The literal value for each type is read from Schema
v1.1's own union declarations and treated as a constant; it is not a computed or
derived value.

Fields populated at Stage 3 for each builder type:

| Builder | Fields populated at Stage 3 | Fields deferred |
|---------|----------------------------|-----------------|
| `ParagraphBuilder` | `kind`, `text` (source block `html` verbatim), `provenance.marker_block_ids`, `provenance.bbox`, `provenance.polygon`, `provenance.page_number` | `provenance.reading_order_index` (Stage 8), `provenance.section_path` (Stage 7), `canonical_path` (Stage 9), `id` (Stage 10) |
| `EquationBuilder` | `kind`, `raw_math` (source block `html` verbatim), `equation_number = None`, provenance fields as above | same deferred set |
| `FootnoteBuilder` | `kind`, `raw_text` (source block `html` verbatim), provenance as above, `attached_object_id = None` | `attached_object_id` (Stage 6), deferred set |
| `ReferenceBuilder` | `kind`, `raw_text` (source block `html` verbatim), provenance as above | deferred set |
| `PageHeaderBuilder` | `kind`, `raw_text` (source block `html` verbatim), provenance as above | deferred set |
| `PageFooterBuilder` | `kind`, `raw_text` (source block `html` verbatim), provenance as above | deferred set |
| `TableBuilder` | `kind`, `raw_html` (source block `html` verbatim), provenance as above, `caption = None`, `rows = []`, `cells = []`, `footnote_ids = []` | `caption` (Stage 4), `rows`/`cells` (Stage 5), `footnote_ids` (Stage 6), deferred set |
| `FigureBuilder` | `kind`, `image_data` (from source block `images` if non-empty, else `None`), provenance as above, `caption = None`, `footnote_ids = []` | `caption` (Stage 4), `footnote_ids` (Stage 6), deferred set |

`CAPTION_TEXT`-classified blocks, `TABLE_CELL_EVIDENCE`-classified blocks, and
`PICTURE`-classified blocks produce no builder at Stage 3. `CAPTION_TEXT` and
`TABLE_CELL_EVIDENCE` are consumed by Stages 4 and 5 respectively by looking them
up in the classified sequence by disposition; `PICTURE` blocks are discarded with a
log entry (§23).

`GENUINE_SECTION_HEADER`-classified blocks produce no builder at Stage 3 either —
`Section` builders are created by Stage 7, because a `Section`'s final shape
cannot be determined until Stage 7 has resolved the full section nesting across all
pages.

### Stage 4: Caption resolution

**Input:** the flat `list[ObjectBuilder]` per page from Stage 3; the
`list[ClassifiedBlock]` from Stage 2 (for adjacent-block lookup); `WrapperContext`
data on each `UnwrappedBlock`.
**Output:** each `TableBuilder` and `FigureBuilder` gains a populated
`caption: CaptionBuilder | None`.

**Pattern A (wrapped).** A `TableBuilder` or `FigureBuilder` whose originating
block has a non-`None` `wrapper_context` uses Pattern A. The sibling `CAPTION_TEXT`
block in the same wrapper is found by scanning the `ClassifiedBlock` sequence for
the entry with `disposition == CAPTION_TEXT` and the same `wrapper_context.block_id`.
This lookup uses `wrapper_context.block_id` matching, not positional index, so it is
correct for both `TableGroup` (`[Caption, Table]` child order) and `FigureGroup`
(`[Figure, Caption]` child order — reversed relative to `TableGroup`).

For Pattern A:

- `CaptionBuilder.kind`: set to the Schema v1.1 literal for `Caption`.
- `CaptionBuilder.label`: extracted via `^(Table|Figure)\s+\d+[\.:]?\s*` regex
  match against the `CAPTION_TEXT` block's `html` content; the matched prefix only
  (e.g. `"Table 3"`), stripped of trailing punctuation. `None` if no match.
- `CaptionBuilder.text`: the remainder of the `CAPTION_TEXT` block's `html` after
  the label prefix (stripped of leading whitespace/punctuation), or the entire
  `html` if no label prefix was found. `None` if the `html` is empty after
  stripping.
- `CaptionBuilder.trailing_notes = None`.
- `CaptionBuilder.provenance.marker_block_ids`: `[caption_block.id,
  wrapper_block.id]`.
- `CaptionBuilder.provenance.bbox = caption_block.bbox` if present.
- `CaptionBuilder.provenance.contributing_bboxes = None`.

**Pattern B (bare).** A `TableBuilder` or `FigureBuilder` whose originating block
has `wrapper_context = None` uses Pattern B. `PICTURE`-classified blocks are
transparent to all adjacency checks in this pattern (they do not count as
intervening blocks).

Adjacent blocks are located by scanning the classified sequence:

- **Label block:** the immediately preceding non-`PICTURE` block must have
  `disposition == CAPTION_LABEL`. If not, caption resolution falls through to
  `None`.
- **Caption-text block:** the non-`PICTURE` block immediately following the
  `CAPTION_LABEL` block (i.e. between the label and the table/figure) must have
  `disposition == BODY_PARAGRAPH`. If not, caption resolution falls through to
  `None`.
- **Trailing-notes block:** the non-`PICTURE` block immediately following the
  `TABLE_SHELL`/`FIGURE_SHELL` block itself, if and only if its `html` content
  starts with the literal prefix `"Note:"` (case-sensitive). Any other content in
  that position is left as `BODY_PARAGRAPH` content for Stage 7, not consumed as
  a trailing note.

For Pattern B:

- `CaptionBuilder.kind`: set to the Schema v1.1 literal for `Caption`.
- `CaptionBuilder.label`: the `CAPTION_LABEL` block's `html` content verbatim.
- `CaptionBuilder.text`: the caption-text block's `html` content verbatim.
- `CaptionBuilder.trailing_notes`: the trailing-notes block's `html` if found,
  else `None`.
- `CaptionBuilder.provenance.marker_block_ids`: `[label_block.id,
  caption_text_block.id]` plus `[trailing_notes_block.id]` if present.
- `CaptionBuilder.provenance.bbox = None` (multiple non-adjacent source blocks).
- `CaptionBuilder.provenance.contributing_bboxes`: list of bboxes of all
  contributing blocks, in order.

**No caption case.** If neither pattern's preconditions are met, `caption = None`.
A log entry is produced (§23).

### Stage 5: Table internal structure

**Input:** `TableBuilder` instances from Stage 3 (with `raw_html` already set),
plus the flat classified sequence (for locating `TABLE_CELL_EVIDENCE` blocks
belonging to each table's original wrapper).
**Output:** each `TableBuilder.rows` populated with `TableRowBuilder` instances;
each `TableBuilder.cells` populated with `TableCellBuilder` instances.

`raw_html` is parsed using a standard HTML table parser (not hand-rolled). For each
`<tr>`, a `TableRowBuilder` is constructed; for each `<th>`/`<td>`, a
`TableRowCellBuilder` is constructed:

- `TableRowCellBuilder.text`: inner content of the `<th>`/`<td>` element, with any
  `<math>...</math>` wrapper tag stripped and its inner content substituted as plain
  text — per finding 3.5 and Schema v1.1 §12.2.
- `TableRowCellBuilder.is_header`: `True` for `<th>`, `False` for `<td>`.
- `TableRowCellBuilder.structural_notes = None`.

**`cells` list for wrapped tables:** The flat `cells` list is populated from
`TABLE_CELL_EVIDENCE`-classified blocks in the same wrapper as this table (located
via `wrapper_context.block_id` matching on the classified sequence — all
`TABLE_CELL_EVIDENCE` blocks sharing this table's `wrapper_context.block_id`). For
each such block, a `TableCellBuilder` is constructed with `text` taken verbatim (not
math-stripped), `bbox` and `polygon` from the source block.

**`cells` list for bare tables (resolves MAJOR-4):** A `TableBuilder` with
`wrapper_context = None` has `cells = []`. `TABLE_CELL_EVIDENCE` blocks are only
present as children of `TableGroup` wrappers (confirmed empirically); a bare `Table`
block has no corresponding flat cell evidence. `cells = []` is a legitimate final
value for bare tables, not an error or placeholder.

No positional correspondence between `rows[i].cells[j]` and `cells[k]` is asserted
or relied upon (Schema v1.1 §12.3 explicitly disclaims this correspondence).

### Stage 6: Footnote attachment

**Input:** `FootnoteBuilder` instances from Stage 3; `TableBuilder` and
`FigureBuilder` instances from the same page (post Stage 5).
**Output:** `FootnoteBuilder.attached_object_id` set (or left `None`);
corresponding `TableBuilder.footnote_ids` or `FigureBuilder.footnote_ids` updated.

**Rule:** for each `FootnoteBuilder` on a page, the candidates are all
`TableBuilder` and `FigureBuilder` instances on the **same page** (never
cross-page) whose `provenance.bbox.y1` (bottom edge) is strictly less than the
footnote's `provenance.bbox.y0` (top edge). Among these candidates, the one with
the maximum `provenance.bbox.y1` is selected. **Tie-break (resolves MAJOR-5):**
if two or more candidates share the same maximum `provenance.bbox.y1`, the one
with the smaller page-array index (i.e. appearing earlier in the page's Stage-2
classified sequence) is selected. This tie-break is deterministic and requires no
additional data beyond what Stage 2 already produces.

If no candidate exists, `attached_object_id` is left `None`.

If a footnote's `provenance.bbox` is `None`, `attached_object_id` is left `None`
and a log entry is produced (§23).

Both sides of the relationship are set atomically: `FootnoteBuilder.attached_object_id`
and the corresponding target's `footnote_ids` list are updated together from the
same single matching result.

### Stage 7: Section tree assembly

**Input:** every page's flat `list[ObjectBuilder]` from Stage 3 (updated through
Stages 4–6); the `section_hierarchy` field of each originating Marker block;
the complete set of `GENUINE_SECTION_HEADER`-classified blocks from Stage 2 across
all pages.
**Output:** the final nested `SectionBuilder` tree; `section_path` populated on
every builder's `ProvenanceBuilder`.

**Multi-page section accumulation.** A single `Section` in a scientific paper
commonly spans multiple pages. The section tree is built once across the entire
document, not independently per page.

The algorithm proceeds in six steps:

**Step 1 — Build the global heading registry.** Traverse `marker_document.children`
(all pages) in reading order. For each `GENUINE_SECTION_HEADER`-classified block
encountered, create a `SectionBuilder` initialized with `heading_text` (from the
source block's `html` verbatim), its `provenance` fields (per Stage 3 provenance
rules), an empty `children` list, and record it in a
`dict[marker_block_id → SectionBuilder]`.

**Step 2 — Resolve each SectionBuilder's depth and parent using reverse lookup
(resolves CRITICAL-2).** `SectionHeader` Marker blocks are not confirmed to carry
their own `section_hierarchy` field; this field is confirmed only on content blocks
(non-heading blocks). Therefore nesting is resolved by reverse lookup: for each
`SectionBuilder`, scan all content blocks across all pages and collect every
`section_hierarchy` dict that references this heading's Marker id. The depth of
this heading is the zero-indexed numeric depth-key position at which its Marker id
appears in those dicts (this value is consistent across all content blocks that
reference it, by Marker's own construction). The parent of a `SectionBuilder` with
depth N is the `SectionBuilder` whose heading Marker id appears at depth-key
position N−1 in the same `section_hierarchy` dicts. A `SectionBuilder` with depth
0 has no parent and is placed directly in a `PageBuilder.children`. A
`SectionBuilder` whose heading Marker id appears in no content block's
`section_hierarchy` at all has no governed content and is omitted from the tree
(Schema v1.1 §9: a `Section` is only materialized if at least one piece of content
is governed by it).

**Step 3 — Resolve each content builder's governing path.** For each non-Section
object builder, take its originating Marker block's `section_hierarchy`, sort
depth-key strings numerically, and resolve each entry to its `SectionBuilder` from
the global registry. The resulting ordered list of `SectionBuilder` references
(outermost first) is the object's governing path. The last (deepest) entry is the
object's immediate parent section. Store the list of Marker block ids (outermost
first) as `ProvenanceBuilder.section_path`. Objects with an empty `section_hierarchy`
(no governing section) have `section_path = []`.

**Step 4 — Place content builders into their immediate parent.** Each content
builder is appended to its immediate parent `SectionBuilder.children`. Objects with
`section_path = []` are appended to the owning `PageBuilder.children`.

**Step 5 — Nest SectionBuilders within each other.** Each `SectionBuilder` with
a parent (determined in Step 2) is appended to that parent `SectionBuilder.children`.
Top-level `SectionBuilder`s (depth 0) are appended to the `PageBuilder.children` of
the page where their heading block appears.

**Step 6 — Establish final children order (resolves CRITICAL-1).** After Steps 4
and 5, each `PageBuilder.children` list and each `SectionBuilder.children` list
contains a mix of content builders and nested `SectionBuilder`s. These are sorted
into their final order by a single rule: **all items in a given `children` list are
ordered by the position of their originating block (the heading block for a
`SectionBuilder`; the source Marker block for a leaf builder) in the page's Stage-2
flat classified sequence, ascending.** The classified sequence's original array
order is the single authoritative ordering source. No secondary sort key is needed
— two items in the same `children` list always originate from different positions
in the classified sequence.

For content that spans multiple pages: a `SectionBuilder`'s children that originate
from different pages are ordered first by page index ascending, then by classified-
sequence position within that page ascending.

**Result:** after Step 6, `section_path` is populated on every content builder's
`ProvenanceBuilder`, and every `PageBuilder.children` and `SectionBuilder.children`
list is in its final, deterministic order.

### Stage 8: Global reading-order assignment

**Input:** fully assembled builder tree from Stage 7.
**Output:** `ProvenanceBuilder.reading_order_index` populated on every builder.

A single depth-first pre-order traversal with a single global counter starting at 0:

1. Iterate `PageBuilder` instances in `page_number` ascending order.
2. Within each `PageBuilder`, iterate `children` in array order (the order
   established by Stage 7 Step 6).
3. When a `SectionBuilder` is encountered: assign it the next counter value, then
   recurse into its `children` (which may themselves contain a mix of leaf builders
   and nested `SectionBuilder`s, processed in array order) before moving to the next
   sibling.
4. When any non-Section builder is encountered: assign it the next counter value;
   no recursion.

A `SectionBuilder.children` list may contain both leaf object builders and nested
`SectionBuilder`s interleaved. The traversal assigns indices in array order,
recursing into any `SectionBuilder` encountered before continuing to the next
sibling — regardless of whether that sibling is a leaf or a nested section.

This is the only stage that writes `reading_order_index` values. No earlier stage
sets a non-`None` value, and no later stage revises one. The counter is shared
across all pages — it is a single global counter for the entire document.

### Stage 9: Canonical path computation

**Input:** fully assembled, reading-order-finalized builder tree.
**Output:** `canonical_path: str` set on every builder.

Per Schema v1.1 §2 and the complete canonical path table in §9 of this
specification, each builder's `canonical_path` is computed from its own
already-fixed tree position. `document_id` is not needed here — Stage 9 computes
paths only; ids are computed in Stage 10.

### Stage 10: Materialization

**Input:** fully assembled, reading-order-finalized, canonical-path-bearing builder
tree; `source_pdf_identifier`; `processing_context`.
**Output:** fully constructed, frozen Schema v1.1 `Document` object.

`document_id = compute_document_id(source_pdf_identifier)` is computed exactly once
at the start of this stage.

**Section materialization order (resolves MAJOR-6):** Section materialization uses
**post-order depth-first traversal** of the `SectionBuilder` tree — recurse into
all children of a `SectionBuilder` and materialize them before constructing the
parent `Section`. This ensures every child is already a frozen model when the
parent `Section` is constructed. For a three-level hierarchy (A contains B contains
C), the materialization order is: C's leaf children → C → B's other children → B →
A's other children → A.

Materialization proceeds bottom-up across the full tree:

1. `TableCellBuilder` → `TableCell`
2. `TableRowCellBuilder` → `TableRowCell`; `TableRowBuilder` → `TableRow`
3. `CaptionBuilder` → `Caption`
4. All leaf builders (`ParagraphBuilder`, `EquationBuilder`, `FootnoteBuilder`,
   `ReferenceBuilder`, `PageHeaderBuilder`, `PageFooterBuilder`) → their
   corresponding frozen models
5. `TableBuilder` (now has materialized `Caption`, `TableRow`, `TableCell`
   children) → `Table`
6. `FigureBuilder` (now has materialized `Caption`) → `Figure`
7. `SectionBuilder`s, via post-order DFS as described above → `Section`
8. `PageBuilder`s (now have materialized children) → `Page`
9. **(resolves MAJOR-7)** `ProcessingMetadata` constructed from `processing_context`:
   `marker_version`, `normalizer_version`, `source_marker_artifact_ref`, and
   `processed_at` transferred verbatim from the `NormalizerProcessingContext` input.
   No field is computed, transformed, or defaulted — all four values are caller-
   supplied and passed through unchanged.
10. **(resolves MAJOR-8)** `Document` assembled with: `pages` (the list of
    materialized `Page` objects from step 8, in `page_number` ascending order),
    `metadata` (assembled in this step from the materialized page list —
    `page_count`, `has_front_matter_page`, `title` as per the rule below),
    `statistics` (assembled in this step by type-counting traversal of the
    materialized page list), `processing_metadata` (from step 9), and
    `source_pdf_identifier` (the `source_pdf_identifier` input parameter, verbatim).
    This `Document` instance is the object passed to Stage 11 and returned to the
    caller if Stage 11 passes.

**Metadata assembly (part of step 10):**
- `Metadata.page_count = len(pages)`
- `Metadata.has_front_matter_page = any(p.is_front_matter for p in pages)`
- `Metadata.title`: the `html` content of the first `GENUINE_SECTION_HEADER`-
  classified block on the first non-front-matter page, taken verbatim. `None` if
  no `GENUINE_SECTION_HEADER` block exists on any non-front-matter page.
- `Statistics.unresolved_footnote_count`: count of `Footnote` objects with
  `attached_object_id is None`.

Each frozen model is constructed with all fields finalized — no field is left at
its builder default of `None` at construction time unless Schema v1.1 explicitly
declares that field as `Optional`.

### Stage 11: Whole-tree validation

See §24 for the complete invariant list. This stage raises on any violation — per
§1's and §2's fail-whole contract.

---

## 6. Ordered Sequence of Stages (Summary Table)

| # | Stage | Primary output | Depends on |
|---|---|---|---|
| 0 | Front-matter detection | `is_front_matter` flags | Raw page text content |
| 1 | Page builder construction | `PageBuilder` shells | Stage 0 |
| 1.5 | Wrapper unwrapping | `list[UnwrappedBlock]` per page | Stage 1 |
| 2 | Block classification | Disposition tags per block | Stage 1.5 |
| 3 | Leaf builder construction | Object builders (partial) | Stage 2 |
| 4 | Caption resolution | `caption` on Table/Figure builders | Stage 3 |
| 5 | Table internal structure | `rows`/`cells` on Table builders | Stage 4 |
| 6 | Footnote attachment | `footnote_ids`/`attached_object_id` | Stage 5 |
| 7 | Section tree assembly | Nested SectionBuilder tree; `section_path` | Stage 6 |
| 8 | Global reading order | `reading_order_index` everywhere | Stage 7 |
| 9 | Canonical path computation | `canonical_path` on every builder | Stage 8 |
| 10 | Materialization | Frozen Schema v1.1 models; `Metadata`/`Statistics`/`ProcessingMetadata`/`Document` | Stage 9 |
| 11 | Whole-tree validation | Pass / raise | Stage 10 |

This ordering is a hard contract.

---

## 7. Rules Governing Deterministic Behavior

1. **No wall-clock or random input affects structural content.** `processed_at` is
   stored verbatim into `ProcessingMetadata` and influences nothing else.
2. **No dict iteration order is relied upon.** `section_hierarchy` dicts are always
   sorted by numeric depth-key before use (Stage 7).
3. **All heuristic thresholds are fixed constants** — the front-matter two-signal
   threshold (Stage 0), the caption-window three-block lookforward (Stage 2), the
   bbox comparison and tie-break in Stage 6.
4. **Identical input invariably produces identical output.** Verified operationally
   via a required test: running `normalize()` twice on the same inputs (with
   `processed_at` held fixed) must produce two `Document` objects whose
   `model_dump_json()` outputs are byte-identical.
5. **Stage ordering is fixed and non-parallelized.**
6. **Builder construction order within a stage is array order** (the unwrapped
   sequence's existing order), never sorted or permuted by the stage itself unless
   the stage description explicitly specifies an ordering operation.

---

## 8. Provenance Propagation Strategy

Every Schema v1.1 object carries a `StructuralProvenance`. Provenance fields are
populated incrementally across stages on the `ProvenanceBuilder`:

| Provenance field | Populated at | Source |
|------------------|-------------|--------|
| `marker_block_ids` | Stage 3 (or Stage 4 for Caption) | Directly from Marker block id(s) |
| `page_number` | Stage 3 | From page index (Stage 1) |
| `bbox` | Stage 3 (or Stage 4 for Caption) | From Marker block `bbox` field |
| `contributing_bboxes` | Stage 3 or 4 | Multi-block sources only (Pattern B captions) |
| `polygon` | Stage 3 | From Marker block `polygon` field |
| `section_path` | Stage 7 | Derived from `section_hierarchy` reverse-lookup resolution |
| `reading_order_index` | Stage 8 | Depth-first traversal counter |

No stage downstream of an object's initial construction ever modifies
`marker_block_ids`, `bbox`, `contributing_bboxes`, or `polygon`. `section_path`
and `reading_order_index` are each written exactly once, at their respective stages.

---

## 9. Identifier Generation and Canonical Path Table

Identifier computation: `id = "doc:" + sha256(document_id + "|" + canonical_path)[:16]`

`document_id` is computed once per document at the start of Stage 10. The complete
`canonical_path` rule for every object type:

| Object type | Canonical path rule | Notes |
|-------------|--------------------|-|
| `Page` | `/page/{page_number}` | 0-indexed array position from Stage 1 |
| `Section` | `{page_canonical_path}/section/{heading_marker_block_id}` | Uses the governing `SectionHeader` block's Marker id; page component is the page where the heading block appears |
| `Paragraph` | `{page_canonical_path}/paragraph/{reading_order_index}` | Page-scoped prefix regardless of Section containment (see note below) |
| `Table` | `{page_canonical_path}/table/{marker_block_id}` | — |
| `TableRow` | `{table_canonical_path}/row/{row_ordinal}` | 0-indexed position in `Table.rows` |
| `TableRowCell` | `{tablerow_canonical_path}/cell/{cell_ordinal}` | 0-indexed position in `TableRow.cells` |
| `TableCell` | `{table_canonical_path}/cell_evidence/{marker_block_id}` | `cell_evidence` namespace avoids collision with `TableRowCell` paths |
| `Figure` | `{page_canonical_path}/figure/{marker_block_id}` | — |
| `Caption` | `{parent_canonical_path}/caption` | Parent is the `Table` or `Figure` |
| `Equation` | `{page_canonical_path}/equation/{reading_order_index}` | Same rationale as `Paragraph` |
| `Footnote` | `{page_canonical_path}/footnote/{marker_block_id}` | — |
| `Reference` | `{page_canonical_path}/reference/{reading_order_index}` | Same rationale as `Paragraph` |
| `PageHeader` | `{page_canonical_path}/page_header/{marker_block_id}` | — |
| `PageFooter` | `{page_canonical_path}/page_footer/{marker_block_id}` | — |

**Path prefix rule for section-nested objects (resolves MINOR-4 from
implementation-readiness audit):** Canonical paths for all objects except `Page`
and `Section` use `{page_canonical_path}` as their prefix regardless of whether
the object is contained in a `Section`. Containment depth is not reflected in
canonical paths. This is a deliberate choice: paths are stable identifiers, not
location strings. An object moved between sections by a future document revision
retains the same `id`.

**Why some objects use `marker_block_id` and others use `reading_order_index`:**
Objects with a 1:1 Marker block use that block's id as the unique path component.
`Paragraph`, `Equation`, and `Reference` objects use `reading_order_index` because
their Marker ids contain a trailing ordinal confirmed non-monotonic with reading
order (finding 3.4) — `reading_order_index` produces paths that are both unique
and ordered by final reading position.

**Uniqueness guarantee:** because `document_id` is fixed per document and each
`canonical_path` is unique within the document, `id` values are unique with
overwhelming probability. Stage 11 invariant 5 (§24) verifies uniqueness directly.

---

## 10. Reading-Order Preservation

Fully specified in Stage 8 (§5). `reading_order_index` is a single global counter
assigned by one traversal, comparable across the entire document regardless of
section nesting depth — the property Schema v1.1 §18 requires.

---

## 11. Section Construction Algorithm

Fully specified in Stage 7 (§5). The six-step algorithm handles multi-page section
accumulation, depth/parent resolution via reverse lookup (not forward-path
assumption), content placement, section nesting, and final children ordering.

---

## 12. Page Construction

Fully specified in Stage 1 (shell) and completed across Stages 2–7. A
`PageBuilder.children` list is not finalized until Stage 7 Step 6.

---

## 13. Paragraph Normalization

Stage 3 and Schema v1.1 §10. `Paragraph.text` is the source Marker block's `html`
verbatim. No content transformation is applied.

---

## 14. Table Normalization

Across Stages 3 (builder shell), 4 (caption), 5 (rows/cells), and 6 (footnote
attachment).

---

## 15. Caption Attachment

Stage 4 (§5) and Schema v1.1 §11. Two-pattern resolution implements finding 3.1.

---

## 16. Figure Normalization

Identical to Table normalization minus Stage 5's row/cell parsing. Stage 4's
Pattern A lookup uses `wrapper_context.block_id` matching (position-independent),
correctly handling `FigureGroup`'s `[Figure, Caption]` child order without
positional assumptions.

---

## 17. Equation Normalization

Stage 3 and Schema v1.1 §14. `raw_math` is verbatim. `equation_number = None`.

---

## 18. Footnote Attachment

Stage 6 (§5) and Schema v1.1 §15. Page-scoped only.

---

## 19. Reference Normalization

Stages 2 (classification) and 3 (construction) and Schema v1.1 §16. `raw_text`
is verbatim.

---

## 20. Metadata Construction

Stage 10 (§5) and Schema v1.1 §5. `Metadata` never gains author/journal/year/DOI
fields at this layer.

---

## 21. Statistics Computation

Stage 10 (§5) and Schema v1.1 §7. All fields are derived counts over the
materialized tree.

---

## 22. Error Handling Philosophy

The Normalizer follows a **fail-loud, fail-whole** philosophy:

- **Pydantic validation errors** propagate immediately.
- **Resolution failures modeled as legitimate outcomes** (`caption = None`;
  `attached_object_id = None`; `Metadata.title = None`) are NOT errors.
- **Unrecognized Marker block types** (not in Stage 2's classification table):
  `UnrecognizedBlockTypeError`. `TableGroup`, `FigureGroup`, and `ListGroup` are
  recognized container types handled by Stage 1.5 and never reach Stage 2's
  classification pass as unrecognized blocks.
- **No retry, fallback parser, or degraded-mode operation.**

Exception types:

```python
class NormalizerError(Exception):
    """Base class for all Normalizer-raised exceptions."""

class UnrecognizedBlockTypeError(NormalizerError):
    block_type: str
    marker_block_id: str
    page_index: int

class WholeTreeInvariantViolationError(NormalizerError):
    invariant_number: int
    description: str
    offending_object_ids: list[str]
```

---

## 23. Logging Strategy

Structured log records at the following points only:

- **Stage 0, per flagged page:** which signals (S1–S4) fired, and whether the
  page was flagged.
- **Stage 2, per `PICTURE` block discarded:** Marker block id, page index.
- **Stage 4, per caption resolved:** pattern used (A or B); or which
  `Table`/`Figure` builder produced `caption = None` and why.
- **Stage 6, per footnote:** whether attached and to which object; whether a
  missing-bbox case prevented matching.
- **Stage 10 completion:** final `Statistics` field set plus
  `processing_context.normalizer_version`.
- **At error time:** full identifying context (Marker block id, page index, stage
  name) before propagating.

No log record contains scientific interpretation of content.

---

## 24. Validation Invariants (Whole-Tree, Stage 11)

1. **Reading order strictly increasing** across the full depth-first traversal of
   the materialized tree.
2. **Every non-`None` `Footnote.attached_object_id` matches the `id` of a `Table`
   or `Figure` that exists in the tree.**
3. **Symmetric footnote-table/figure consistency:** every `Table`/`Figure.footnote_ids`
   entry matches the `id` of a `Footnote` in the tree whose `attached_object_id`
   points back to this same `Table`/`Figure`.
4. **Every object's `section_path` matches an actual ancestor `Section` chain in
   the final tree.**
5. **No two objects in the tree share the same `id`.**
6. **`Document.pages` is sorted ascending by `page_number` with no duplicates.**
7. **Every count in `Statistics` matches an independent re-traversal:** a second
   recursive tree walk using a separate counting function compares field-by-field
   against Stage 10's assembled `Statistics`; any discrepancy raises
   `WholeTreeInvariantViolationError` with `invariant_number=7`.
8. **(resolves MAJOR-3) Every builder constructed in Stage 3 appears exactly once
   in the materialized tree — neither omitted nor duplicated.** Checked by
   collecting the set of `id` values of all materialized leaf and composite objects
   and comparing it against the set of expected objects derived from Stage 3's
   output list. Builders excluded from this check (legitimate non-tree participants):
   those originating from `CAPTION_TEXT`-classified blocks (consumed into
   `Caption` objects, checked indirectly via invariant 2/3 equivalents),
   `TABLE_CELL_EVIDENCE`-classified blocks (checked via `Table.cells` membership),
   and `PICTURE`-classified blocks (legitimately discarded). All other Stage-3
   builders must appear in the tree exactly once.

---

## 25. Extension Points for Future Marker Versions

- **Stage 2's classification table** is the single point for every recognized
  `block_type`. A new Marker block type requires exactly one addition here.
- **Stage 1.5's unwrapper** lists all wrapper block types. A new wrapper type
  requires exactly one addition here plus one `WrapperContext.wrapper_type` value.
- **Stage 0's front-matter signals** are an explicit four-signal table. New signals
  require a confirmed representative paper.
- **Stage 4's caption patterns** are a named two-pattern enumeration. A third
  pattern follows the same template without touching A or B.
- **Stage 6's footnote-matching strategy** is one geometric strategy. A second
  strategy is added alongside it; arbitration is deferred until designed.

---

## 26. Explicit Boundaries with Later Phases

- **Retrieval:** building any query interface over the finished `Document`.
- **Extraction:** recognizing treatments, species, variables, traits, or any
  scientific entity from text fields.
- **IR construction:** `Treatment`, `Observation`, `Measurement`, etc. Parsing
  `Reference.raw_text` into author/year/journal/DOI is IR-layer only.
- **Validation (scientific):** unit consistency, impossible-value detection,
  ontology compliance.
- **Scientist Review:** any UI, approval workflow, or evidence presentation.
- **BETYdb Export:** any mapping from IR objects to BETYdb schema or records.

---

## Appendix A: Issue Resolution Index

Every issue from the v1.0-draft freeze review and the v1.0 implementation-readiness
audit is listed here with a pointer to its resolution.

### From v1.0-draft freeze review (resolved in v1.0, carried forward)

- **CRITICAL-1** (frozen model population contradiction): §4.1 builder pattern.
- **CRITICAL-2** (TableGroup/FigureGroup/ListGroup unwrapping undefined): §4.2 and
  §5 Stage 1.5.
- **MAJOR-1** through **MAJOR-10**, **MINOR-1** through **MINOR-8**: resolved in
  v1.0; see v1.0 revision record.

### From v1.0 implementation-readiness audit (resolved in v1.1)

- **CRITICAL-1** (ungoverned content and Section interleaving order unspecified):
  §5 Stage 7 Step 6.
- **CRITICAL-2** (SectionBuilder nesting assumed SectionHeader blocks carry
  `section_hierarchy`): §5 Stage 7 Step 2 — replaced with reverse-lookup algorithm.
- **CRITICAL-3** (`kind` discriminator never assigned): §4.1 `kind` field rule;
  §5 Stage 3 `kind` field assignment paragraph.
- **CRITICAL-4** (Stage 2 CAPTION_LABEL lookahead used not-yet-assigned
  dispositions): §5 Stage 2 CAPTION_LABEL override rule — changed to `block_type`
  check.
- **MAJOR-1** (S4 referenced undefined "section-heading vocabulary"): §5 Stage 0
  S4 row — changed to structural `block_type == "SectionHeader"` check.
- **MAJOR-2** (builder field lists incomplete for most types): §4.1 complete builder
  field rule.
- **MAJOR-3** (§24 missing invariant for Stage-3 object coverage): §24 invariant 8.
- **MAJOR-4** (no rule for `cells` list of bare tables): §5 Stage 5 bare-tables
  paragraph.
- **MAJOR-5** (Stage 6 tie-break unspecified): §5 Stage 6 tie-break clause.
- **MAJOR-6** (Stage 10 Section materialization order unstated): §5 Stage 10 post-
  order DFS paragraph.
- **MAJOR-7** (`ProcessingMetadata` construction absent from Stage 10 steps): §5
  Stage 10 step 9.
- **MAJOR-8** (`Document` root constructor call never specified): §5 Stage 10
  step 10.
- **MINOR-4** (canonical path prefix for section-nested objects ambiguous): §9
  path prefix rule paragraph.