# Document Schema Specification

**Project:** LLM-Assisted Extraction of Agronomic and Ecological Experiments into Structured Data
**Layer:** Document Understanding Layer (Document Object only)
**Status:** Draft for review — intended to be frozen upon approval
**Predecessor artifact:** Raw Marker Model (`marker_adapter/raw_model.py`), frozen
**Empirical basis:** `Marker Output — Empirical Findings (Paper 1: Nutrient Cycling, Smukler et al. 2012)`

This document is an engineering specification, not an implementation. It defines every
object in the canonical Document layer — its purpose, fields, types, relationships,
identifier rule, provenance rule, validation rules, and serialization requirements —
so that implementing the Pydantic v2 Document Object later requires translation, not
design. No parsing, normalization, or business logic is described here; only the shape
of the data those future components will populate.

---

## 0. Relationship to the Raw Marker Model

The Raw Marker Model is a lossless, uninterpreted mirror of Marker's JSON output: a
single `MarkerBlock` envelope type, `extra="allow"`, no discriminated union, no
semantic interpretation. The Document Object described here is the next layer down
the pipeline: it is produced *from* the Raw Marker Model by the Normalizer (not yet
implemented) and is the first place where **structural** interpretation occurs —
deciding what counts as a Table, a Section, a Footnote's likely attachment — while
still containing zero scientific meaning.

Every Document-layer object therefore exists in addition to, not instead of, the Raw
Marker Model. The Raw Marker Model remains the permanent ground truth on disk;
the Document Object is a derived, queryable, typed structural view over it. This
specification assumes the Raw Marker Model is available as an immutable input and
focuses entirely on what the Normalizer must produce from it.

---

## 1. Architectural Invariants

These rules are not per-object — they govern the entire Document layer and every
object defined below conforms to them without restating them per-section.

**1.1 Immutability.** Every Document-layer model is frozen after construction
(Pydantic v2 `model_config = ConfigDict(frozen=True)`). No object is mutated after
the Normalizer finishes building it. Corrections, re-interpretation, or review
happen in later layers (IR, Scientist Review) and never write back into the
Document Object.

**1.2 Structural-only content.** No Document-layer object may contain a field whose
purpose is to record scientific meaning. Concretely: no `treatment`, `species`,
`observation`, `management_event`, `variable`, or `trait` field exists anywhere in
this schema, even as an optional placeholder. If a future need arises to record such
a concept, it belongs in the IR, which is built on top of — never inside — the
Document Object.

**1.3 Deterministic identifiers.** No identifier in this schema is a UUID4 or any
other non-deterministic value. Every identifier is a pure function of stable inputs,
so that re-running the same PDF through the same Marker version and the same
Normalizer version always yields byte-identical identifiers. The exact construction
rule is given in Section 2.

**1.4 Maximum available provenance.** Every object that originates from one or more
Marker blocks retains a `StructuralProvenance` value (Section 3.3) referencing the
originating Marker block id(s), page number, bounding box, polygon, and reading-order
position. An object is never permitted to "lose" its Marker origin even when the
Normalizer reshapes or merges multiple Marker blocks into one Document object (e.g.
turning a `SectionHeader` + `Text` pair into one normalized `Caption`).

**1.5 Deterministic, lossless serialization.** Every model in this schema must
support `model_dump()` / `model_dump_json()` and round-trip back through
`model_validate()` without information loss, exactly as already verified for the
Raw Marker Model. Field ordering in dumped JSON is determined by declaration order
in the Pydantic model (not insertion order at runtime) to keep serialized output
byte-stable across runs.

**1.6 Independence from downstream layers.** Nothing in this schema imports from,
references, or anticipates retrieval, LLM extraction, validation, the IR, or BETYdb
export. The Document Object's public surface is consumed by those layers, but this
schema has zero knowledge of them.

---

## 2. Identifier Strategy

**Rule.** Every Document-layer object's `id` is computed as:

```
id = "doc:" + sha256( document_id + "|" + canonical_path )[:16]
```

where `document_id` is the parent Document's own id (Section 4), and
`canonical_path` is a deterministic structural path string specific to each object
type, defined per-object below (generally derived from the originating Marker
block's own path-like id, e.g. `/page/7/Table/2`, when one exists 1:1; or, for objects
synthesized from multiple Marker blocks or with no direct Marker counterpart — such
as a parsed `TableRow` — a path built from the parent object's id plus an ordinal
position among deterministically-ordered siblings, e.g. `.../Table/2/row/3`).

**Why a hash rather than reusing Marker's path id directly.** Marker's own ids
(`/page/7/Table/2`) are positional/index-based — `Table/2` means "third
Table-typed block encountered in that page's traversal." If a future Marker version
changes internal traversal order, encounters a new block type, or reorders block
discovery, these indices could silently shift between runs on an unchanged PDF,
producing different "stable" ids for the same content. Hashing a path that is
itself still derived from Marker's structure, combined with the document id,
preserves determinism for a fixed Marker/adapter version while making the contract
explicit: **stability is guaranteed within one Marker version, not promised across
Marker upgrades.** The original Marker path is never discarded — it is preserved
verbatim inside every object's `StructuralProvenance.marker_block_id` — so a Marker
version bump that changes traversal order is detectable (ids change) and
diagnosable (provenance still shows the old vs. new Marker ids).

**document_id construction.** `document_id = "betydoc:" + sha256(source_pdf_identifier)[:16]`,
where `source_pdf_identifier` is a stable external identifier for the source PDF
(DOI if known, else a content hash of the source PDF bytes). This deliberately
excludes Marker version and timestamp from the identity computation: the same PDF
must always resolve to the same `document_id` so that re-processing (e.g. after a
Normalizer bug fix) updates the same logical Document Object rather than minting an
unrelated one. Marker version and processing time are recorded as **metadata about
the materialization**, not folded into identity — see `ProcessingMetadata` (Section
6).

**Properties guaranteed by this scheme:**
- Same PDF + same Marker version + same Normalizer version ⇒ identical ids
  throughout the tree.
- Ids are opaque strings, safe to use as dictionary keys, filenames, or database
  foreign keys.
- Every id is traceable backward to a concrete Marker block via
  `StructuralProvenance`, satisfying invariant 1.4.

---

## 3. Foundational Supporting Types

These are not top-level entities; they are embedded value objects used throughout
the schema.

### 3.1 BoundingBox

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `x0` | float | yes | Marker-observed | Left edge |
| `y0` | float | yes | Marker-observed | Top edge |
| `x1` | float | yes | Marker-observed | Right edge |
| `y1` | float | yes | Marker-observed | Bottom edge |

Directly carried over from Marker's `bbox` (already typed as `MarkerBBox` in the Raw
Marker Model). Retained at the Document layer because footnote-to-table attachment,
evidence highlighting in the Scientist Review UI, and any future geometric
reconstruction (e.g. merged-cell heuristics) all require it. **Invariant:** `x1 >=
x0` and `y1 >= y0`; the Normalizer is responsible for not constructing a violating
instance, but the model also validates this on construction since the cost of
allowing silently-inverted boxes downstream is high (evidence UI would render
boxes wrong with no error signal).

### 3.2 Polygon

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `points` | list of 4 `(float, float)` pairs | yes | Marker-observed | Carried over from Marker's `polygon` |

Retained even though `BoundingBox` is derivable from it, because Marker provides
both independently and the polygon can in principle capture skew that an
axis-aligned bbox cannot. This is a direct empirical carry-over (already present and
typed in the Raw Marker Model) rather than a new design — Document-layer objects
simply forward it unchanged. No Document-layer object computes one from the other;
both come from Marker as-is.

### 3.3 StructuralProvenance

This is the single most important supporting type in the schema — it is what
satisfies invariant 1.4 for every object below.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `marker_block_ids` | list of str | yes (min length 1) | Marker-observed | The originating Marker block id(s), e.g. `["/page/7/Table/2"]`. A list, not a single value, because some Document objects (e.g. a normalized `Caption` under Pattern B) are synthesized from more than one Marker block. |
| `page_number` | int | yes | Marker-observed | The PDF page this object originates from. For objects spanning conceptually across the synthesis of multiple Marker blocks, this is the page of the primary/first contributing block. |
| `bbox` | `BoundingBox` | no | Marker-observed | Present for any object with a single, well-defined originating region. Absent for objects synthesized from multiple non-adjacent blocks where a single bbox would be misleading (e.g. a Pattern-B caption combining a `SectionHeader` far above a trailing `Text` note) — in that case `contributing_bboxes` is populated instead. |
| `contributing_bboxes` | list of `BoundingBox` | no | Marker-observed | Used instead of (or in addition to) `bbox` when more than one Marker block contributes geometry, preserving each one rather than collapsing them into a single misleading box. |
| `polygon` | `Polygon` | no | Marker-observed | Mirrors `bbox`'s optionality logic. |
| `reading_order_index` | int | yes | Architectural requirement | The object's position in the document's global linear reading order (Section 3.4). Required on every provenance instance because every structural object has a place in reading order even if its bbox is ambiguous. |
| `section_path` | list of str | yes (may be empty) | Marker-observed (derived) | The chain of governing `SectionHeader` Marker-block ids from Marker's own `section_hierarchy` map, ordered outermost to innermost. Empty only for objects outside any section (e.g. a journal wrapper page's `Picture`). |

**Why a list of Marker block ids rather than exactly one.** Empirically, not every
Document-layer concept maps 1:1 to a Marker block. The clearest case is `Table`
captions: under Pattern A (`TableGroup`), the caption is one `Caption` block; under
Pattern B (bare `Table`), the equivalent information is split across a
`SectionHeader` block and a `Text` block, sometimes with a trailing "Note:" `Text`
block. Forcing a single-id provenance field would require silently picking one
contributing block and losing the others. A list preserves all of them, satisfying
invariant 1.4 even when normalization merges several Marker blocks into one
Document concept.

### 3.4 Reading Order

Reading order is **not** a field on a supporting type — it is a global integer
sequence assigned by the Normalizer to every leaf and container object during
construction, equal to that object's position in a single depth-first traversal of
the final Document Object tree, in `children` array order.

This decision is made explicitly here because it was a confirmed empirical finding,
not a default assumption: Marker's own block id local-index numbers (e.g. the
trailing `4` in `/page/7/Footnote/4`) are **not** monotonic with true reading order —
`Footnote/4` and `Footnote/5` physically appear, in the actual children array, after
`Table/8`, despite having lower index numbers. Reading order must therefore be
(re)computed by the Normalizer from final tree position, never inferred from Marker's
id numbering. `StructuralProvenance.reading_order_index` is this recomputed value,
not a copy of any number embedded in a Marker id string.

### 3.5 Section Path

`StructuralProvenance.section_path` is populated directly from Marker's own
`section_hierarchy` dict, which the empirical findings confirmed is already a
precomputed breadcrumb (e.g. a deeply nested `TableCell` carrying
`{'1': '/page/1/SectionHeader/1', '4': '/page/7/SectionHeader/0'}`). Two properties
of this dict are carried forward into the spec rather than assumed away:

- **Depth keys are not contiguous small integers.** The observed keys were `'1'`
  and `'4'`, not `'1'` and `'2'`, indicating these correspond to some absolute
  nesting depth from Marker's internal traversal rather than a clean rank. The
  Document schema therefore stores `section_path` as an **ordered list of
  SectionHeader Marker-block ids** (sorted by the numeric value of their original
  dict key) rather than preserving Marker's dict-with-gaps shape — this gives
  downstream consumers (Retrieval layer, Section nesting) a clean, ordinary list
  without forcing them to understand Marker's internal depth-key semantics.
- **The mapping is per-block, not per-Section-object.** Every Marker block —
  including deeply nested ones like a `TableCell` — carries its own full path. The
  Document Object's `Section` containment hierarchy (Section 9) is derived from this
  same data, so `section_path` on any object and that object's ancestor `Section`
  chain are guaranteed consistent by construction, not by a separate invariant check.

---

## 4. Document

**Purpose.** The root container for one processed paper. Holds the page sequence,
top-level metadata, processing metadata, and aggregate statistics. Exactly one
`Document` exists per source PDF per Normalizer run.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | `document_id`, Section 2. |
| `source_pdf_identifier` | str | yes | Architectural requirement | The stable external identifier used to compute `id` (DOI or content hash). Stored explicitly so the id's derivation is independently checkable, not just trusted. |
| `metadata` | `Metadata` | yes | Marker-observed + Architectural | Section 5. |
| `processing_metadata` | `ProcessingMetadata` | yes | Architectural requirement | Section 6. |
| `statistics` | `Statistics` | yes | Architectural requirement | Section 7. |
| `pages` | list of `Page` | yes (min length 1) | Marker-observed | Ordered by page number ascending; this ordering is also the top level of global reading order. |

**Invariants.**
- `pages` is non-empty and sorted ascending by `Page.page_number` with no
  duplicate or skipped page numbers other than what Marker itself reported (a
  Marker-side page omission is preserved, not silently re-numbered).
- `Document` is the only object in this schema with no `StructuralProvenance` of
  its own (there is no single Marker block representing "the whole document" — the
  Raw Marker Model's root node was empirically confirmed to have no `id`, `bbox`,
  or `polygon` at all). Its provenance is implicitly "the entire Raw Marker Model
  file," which `processing_metadata.source_marker_artifact_ref` captures (Section
  6) rather than a `StructuralProvenance` instance.

---

## 5. Metadata

**Purpose.** Bibliographic and identification facts about the paper, to the extent
they are structurally recoverable (not semantically extracted — see the boundary
note below).

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `title` | Optional[str] | no | Marker-observed | Taken verbatim from the first/top-level `SectionHeader` or title-styled block on the front matter page, if structurally identifiable. |
| `page_count` | int | yes | Marker-observed | Count of `Page` objects; redundant with `len(pages)` but kept as an explicit field since `Statistics` (Section 7) is meant to hold *derived counts*, while this one is a basic identifying fact worth surfacing without traversing the tree. |
| `has_front_matter_page` | bool | yes | Marker-observed (heuristic) | Whether page 0 (or any page) was structurally flagged as publisher wrapper content. See `Page.is_front_matter` (Section 8) for the per-page flag this aggregates. |

**Boundary note.** `Metadata` deliberately does **not** include authors, journal
name, publication year, or DOI as structured fields, even though these are
intuitively "metadata." Per the empirical findings (3.8), front-matter and
citation-bearing content is **structurally indistinguishable** from other text at
the block-type level — recovering "the authors" or "the journal" requires reading
and interpreting text content, which is scientific/semantic extraction, not
structural parsing. That work belongs to the IR's `Citation` entity (already
specified in the project's broader IR design), built by the extraction layer. This
spec only exposes what is mechanically true of the page structure (title block
location, page count, front-matter flag) — adding speculative `author`/`doi`/`year`
fields here would violate invariant 1.2 and the "no speculative fields" instruction,
since populating them correctly is not a structural operation.

---

## 6. ProcessingMetadata

**Purpose.** Records *how* this particular Document Object was produced, separate
from *what* it identifies (Section 4's `id`/`source_pdf_identifier`). This is what
makes reproducibility checkable: two Document Objects with the same `id` but
different `ProcessingMetadata` indicate the same paper was processed by a different
Marker or Normalizer version, which is exactly the signal needed to detect drift
without conflating it with document identity.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `marker_version` | str | yes | Marker-observed | Verbatim from Marker's own output metadata, if present; otherwise the version string of the Marker invocation recorded by the adapter. |
| `normalizer_version` | str | yes | Architectural requirement | Semantic version of the Normalizer code that produced this Document Object. Required so a future schema/logic change is always attributable. |
| `processed_at` | datetime (ISO 8601, UTC) | yes | Architectural requirement | Wall-clock time of this materialization. Explicitly **not** part of `id` computation (Section 2) — recorded for audit/debugging only. |
| `source_marker_artifact_ref` | str | yes | Architectural requirement | A path or content hash identifying the exact Raw Marker Model JSON file this Document Object was normalized from, satisfying the "Document has no own provenance" note in Section 4 by pointing at the file-level artifact instead of a block-level one. |

**Why this is architectural rather than Marker-observed for most fields.** Only
`marker_version` comes from Marker itself; the rest exist purely because the
project's stated reproducibility requirement ("identical PDFs ... should always
produce identical Document Objects," and detectability of drift) demands a place to
record the inputs that determine reproducibility, even though Marker's own output
has no opinion on them.

---

## 7. Statistics

**Purpose.** Aggregate counts over the final Document Object tree, useful for
sanity-checking a Normalizer run (e.g. "did this paper produce zero tables when the
PDF clearly has six") without re-traversing the tree ad hoc.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `page_count` | int | yes | Architectural requirement (derived) | `len(pages)`. |
| `section_count` | int | yes | Architectural requirement (derived) | Total `Section` objects across the document. |
| `paragraph_count` | int | yes | Architectural requirement (derived) | Total `Paragraph` objects. |
| `table_count` | int | yes | Architectural requirement (derived) | Total `Table` objects. |
| `figure_count` | int | yes | Architectural requirement (derived) | Total `Figure` objects. |
| `equation_count` | int | yes | Architectural requirement (derived) | Total `Equation` objects. |
| `footnote_count` | int | yes | Architectural requirement (derived) | Total `Footnote` objects. |
| `reference_count` | int | yes | Architectural requirement (derived) | Total `Reference` objects. |
| `unresolved_footnote_count` | int | yes | Architectural requirement (derived) | Footnotes whose `attached_object_id` (Section 16) is `None` after Normalizer processing — a direct, queryable signal of how much of the geometric-attachment heuristic (empirical finding 3.2) succeeded on this paper. |

**Why this object exists at all, given everything in it is derivable.** Every
field here is computable by traversal, so in principle `Statistics` adds no new
information. It exists as an explicit object — rather than leaving consumers to
compute it themselves — because (a) it gives a single, serializable snapshot for
logging/comparison across Normalizer runs without re-parsing the whole tree, and (b)
`unresolved_footnote_count` specifically operationalizes a concern raised directly
in the empirical findings (footnote attachment is a heuristic, not guaranteed) into
a number that can be tracked across the representative paper set as the Normalizer
is built and tuned.

---

## 8. Page

**Purpose.** One PDF page's structural content, in reading order.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2; `canonical_path = "/page/{page_number}"`. |
| `page_number` | int | yes | Marker-observed | Zero-indexed, matching Marker's own page numbering. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the Marker Page block's id]`. |
| `children` | list of (`Section` \| `Paragraph` \| `Table` \| `Figure` \| `Equation` \| `Footnote` \| `PageHeader` \| `PageFooter`) | yes (may be empty) | Marker-observed | Top-level content of the page, in final reading order (Section 3.4). A discriminated union over `block_type`-equivalent kinds, mirroring (but not reusing) Marker's own children-array structure. |
| `is_front_matter` | bool | yes | Marker-observed (heuristic) | True if this page was identified as publisher wrapper content (journal cover, "Submit your article," ISSN-only content, etc.) rather than paper body. |

**On `is_front_matter`.** Empirical finding 3.8 established that Marker gives no
structural signal distinguishing a wrapper page from a content page — both use
identical block types. This flag is therefore explicitly a **heuristic output of
the Normalizer** (content-pattern based, e.g. presence of "ISSN," "Submit your
article," near-total absence of citation-bearing text), not something copied from
Marker. The field is included now, with its value to be computed later, because the
project's stated requirement is that the schema accommodate this known case without
redesign — per the same logic as the other deferred-population fields in this spec
(Section 22 collects all of them explicitly).

**Why a discriminated union for `children` rather than `list[Any]` or one generic
`Block` type.** The Raw Marker Model deliberately uses one uniform envelope because
it must stay agnostic to block semantics. The Document Object's job is the opposite:
it exists specifically to make structural type distinctions (a `Table` is not
interchangeable with a `Paragraph` downstream). A discriminated union gives
consumers static type safety and keeps `Page`/`Section` children lists
self-describing in serialized JSON via the discriminator field, with no loss of
ordering since list order is itself the reading-order signal (Section 3.4).

---

## 9. Section

**Purpose.** A heading-governed grouping of content, derived from Marker's
`section_hierarchy` breadcrumbs (Section 3.5) rather than re-derived from text
pattern-matching on headings.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | `canonical_path` built from the governing `SectionHeader` Marker block's own path id. |
| `heading_text` | str | yes | Marker-observed | Verbatim text of the governing `SectionHeader` block. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the SectionHeader block's id]`. |
| `depth` | int | yes | Marker-observed (derived) | Position of this section's heading in the ordered `section_path` list (Section 3.5), zero-indexed from the outermost heading on the page/document. |
| `children` | list of (`Section` \| `Paragraph` \| `Table` \| `Figure` \| `Equation` \| `Footnote`) | yes (may be empty) | Marker-observed | Nested sub-sections and content governed by this heading, in reading order. A `Section` may contain further `Section` objects, giving the hierarchy genuine nesting rather than a flat list with a depth integer alone. |

**Invariant.** Every leaf or container object elsewhere in the schema that carries
a non-empty `section_path` in its `StructuralProvenance` must have a corresponding
ancestor chain of `Section` objects matching that path exactly — this is guaranteed
by construction (both are derived from the same `section_hierarchy` source, per
Section 3.5) rather than checked as a runtime validator, but it is stated here as a
hard design invariant the Normalizer must not violate.

**Why `SectionHeader` blocks that are really table/figure labels (e.g. a Marker
`SectionHeader` containing only `"Table 3"`, per Pattern B) do not become `Section`
objects.** Empirical finding 3.1 showed Marker uses the same `SectionHeader`
block type both for genuine paper sections (Methods, Results) and for bare-table
caption labels. The Normalizer must distinguish these by context — a
`SectionHeader` immediately followed by a `Text` block and then a `Table`, with no
intervening structural content, is a caption label being consumed into that
`Table`'s `Caption` (Section 12), not a new `Section`. This rule is recorded here so
the schema's `Section` object is understood to represent only genuine paper
sections; the disambiguation logic itself is Normalizer business logic (out of
scope for this document) but the *consequence* — that some `SectionHeader` Marker
blocks become part of a `Caption` rather than a `Section` — is a structural decision
the schema must support, and it does: `Caption.provenance.marker_block_ids` can
include a `SectionHeader` id (Section 12).

---

## 10. Paragraph

**Purpose.** A single block of body text — the most common leaf content type.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2. |
| `text` | str | yes | Marker-observed | The block's inline HTML content from Marker, **as-is** (e.g. `<b>`, `<a href>` tags preserved). |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the originating Text/ListItem block's id]`. |

**Why `text` keeps inline HTML rather than being plain-text-stripped.** Empirical
finding (leaf block dump) confirmed Marker leaf blocks carry real semantic inline
markup (`<b>`, `<a href>`) directly in their content, not a side annotation. Stripping
it at the Document layer would be a one-way, lossy transformation performed before
any consumer has had a chance to decide whether that markup matters (e.g. a `<b>`
emphasis inside a Methods paragraph could matter to the extraction layer's reasoning
about emphasis on a key term). Per invariant 1.4 (maximum available provenance) and
the general "never lose information without a consumer-side decision to do so"
principle, the Document layer preserves it verbatim; any stripping is a retrieval-
or extraction-layer concern, explicitly out of scope here.

**Note on `ListItem`/`ListGroup`.** Marker's bibliography uses `ListGroup` containers
of `ListItem` leaves rather than `Text` blocks (this was the basis for separating
references structurally without text pattern-matching). A `ListItem` that is part of
a reference list is **not** modeled as a `Paragraph` — it becomes a `Reference`
(Section 17). A `Paragraph` is reserved for body-text `Text`/generic `ListItem`
content; the Normalizer disambiguates by parent context (a `ListGroup` under the
References section vs. elsewhere), again business logic out of scope here, but the
schema accommodates the distinct outcome via two separate object types.

---

## 11. Caption (supporting type, embedded in Table and Figure)

**Purpose.** A normalized representation of a table or figure's caption,
collapsing Marker's two empirically observed patterns into one shape.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `label` | Optional[str] | no | Marker-observed | E.g. `"Table 3"` or `"Figure 1"`. Present whenever a `Caption` block (Pattern A) or a `SectionHeader` label block (Pattern B) was found. |
| `text` | Optional[str] | no | Marker-observed | The descriptive caption sentence. From the `Caption` block's content (Pattern A) or the `Text` block immediately following the label (Pattern B). |
| `trailing_notes` | Optional[str] | no | Marker-observed | The trailing "Note: ..." `Text` block sometimes observed immediately after a `Table`, distinct from both `label`/`text` and from `Footnote` objects (Section 16). Kept as its own field because it was empirically observed to be part of the caption apparatus, not body text, but also not a true Marker `Footnote` block. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids` lists every contributing Marker block (one for Pattern A's single `Caption` block; two or three for Pattern B's `SectionHeader` + `Text` + optional trailing `Text`). Uses `contributing_bboxes` (Section 3.3) rather than a single `bbox` whenever more than one block contributes, since collapsing non-adjacent regions into one bbox would misrepresent the geometry. |

**Why one normalized shape rather than preserving Marker's two patterns
separately in the schema.** This is the central case the project's "empirically
driven, not speculative" instruction is built around: both patterns were directly
observed (Pattern A on pages 6/10/12, Pattern B on page 7, per finding 3.1), so
normalizing them is not a hypothetical convenience — it is required because every
downstream consumer (extraction layer asking "what is this table about," review UI
displaying "the caption") needs one consistent shape regardless of which pattern the
source PDF happened to produce. Modeling them as two different optional sub-objects
instead would push that disambiguation work onto every consumer rather than once,
inside the Normalizer, where the empirical knowledge of the two patterns actually
lives.

---

## 12. Table

**Purpose.** A table's logical structure and its evidence-level cell geometry,
kept as two deliberately parallel representations per the empirical recommendation.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the Table block's id]` (and the `TableGroup` id too, if Pattern A). |
| `caption` | Optional[`Caption`] | no | Marker-observed | Section 11. `None` only if no caption-bearing blocks were found adjacent to the table at all (not empirically observed in the representative paper, but not excluded as a possibility — captionless tables are not assumed impossible). |
| `raw_html` | str | yes | Marker-observed | The Table block's own `html` field, verbatim — the complete, correctly-nested `<table>...</table>` Marker produces. Treated as the **source of truth for logical structure** (rows, columns, header rows), per the empirical recommendation, precisely because reconstructing structure independently from cell geometry risks disagreeing with Marker's own (already correct) parse. |
| `rows` | list of `TableRow` | yes (may be empty) | Marker-observed (derived) | A structured parse of `raw_html`'s `<tr>` elements into row objects (Section 12.1), giving consumers row/column access without re-parsing HTML themselves. Derived from `raw_html`, not an independent reconstruction. |
| `cells` | list of `TableCell` | yes (may be empty) | Marker-observed | The flat list of Marker `TableCell` child blocks, retained **only** as evidence/geometry data (bbox, polygon, provenance) — explicitly not used to derive row/column structure, per the empirical recommendation that `raw_html` is structural truth and `TableCell` geometry is supplementary. |
| `footnote_ids` | list of str | yes (may be empty) | Architectural requirement (deferred population) | Ids of `Footnote` objects geometrically attached to this table (Section 16). Empty until the Normalizer's bbox-proximity heuristic (finding 3.2) runs; the field exists now so that heuristic's output has a defined home without later schema change. |

### 12.1 TableRow (supporting type, embedded in `Table.rows`)

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `cells` | list of `TableRowCell` | yes | Marker-observed (derived) | Ordered left to right per the source `<tr>`. |

### 12.2 TableRowCell (supporting type, embedded in `TableRow.cells`)

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `text` | str | yes | Marker-observed | Cell text content from the parsed `<th>`/`<td>` element, with any `<math>` wrapper tag stripped and its content treated as equivalent plain text (per empirical finding 3.5 — Marker inconsistently wraps numerically identical `mean ± stderr` values in `<math>` depending on OCR path; the schema does not preserve this distinction since it carries no structural meaning, only an OCR-routing artifact). |
| `is_header` | bool | yes | Marker-observed | True if the source element was `<th>`, false for `<td>`. |
| `structural_notes` | Optional[str] | no | Architectural requirement (deferred) | A free-text slot reserved for a Normalizer-attached structural annotation — most notably, a suspected merged-cell placeholder (empirical finding 3.4: Marker silently flattens merged header cells into duplicated rows with an empty filler cell, with no flag distinguishing this from a genuinely empty cell). The heuristic for populating this field is explicitly **not** decided in this specification — finding 3.4 was flagged as needing more representative papers before a reconstruction rule is chosen. The field is included as an open slot precisely so that decision can be made later without a schema change, consistent with the brief's instruction to accommodate known structural cases without redesign. |

**Why `TableRowCell` does not have `row_index`/`col_index` integers.** These are
implicit in `Table.rows`' list-of-lists structure itself (a cell's row is its
containing `TableRow`'s position in `rows`; its column is its own position in
`cells`), so adding redundant integer fields would duplicate information already
present in list order, with no Marker-observed justification for storing it twice.

**Why `TableRowCell` has no `rowspan`/`colspan` field.** Empirical finding 3.4
confirmed Marker's HTML output never emits `rowspan`/`colspan` attributes even where
the source PDF visually has merged cells — it flattens instead. Adding a
`rowspan`/`colspan` field for a case never observed in Marker's actual output would
violate the "no speculative fields" instruction. If a future representative paper
demonstrates Marker does emit span attributes under some condition, this is the
single place such fields would be added.

### 12.3 TableCell (supporting type, embedded in `Table.cells`; evidence-only)

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2; path derived from the Marker `TableCell` block's own id. |
| `text` | str | yes | Marker-observed | Verbatim cell content (not math-stripped here — this object is evidence/geometry, not the logical text consumers should read; `TableRowCell.text` is the cleaned version). |
| `bbox` | `BoundingBox` | yes | Marker-observed | Per-cell geometry, the entire reason this parallel representation is retained (evidence highlighting in the review UI). |
| `polygon` | `Polygon` | yes | Marker-observed | Mirrors `bbox`. |

**Why this evidence-only `TableCell` and the logical `TableRowCell` are not unified
into one type.** Empirical finding 3.3 established these are genuinely two
different, only partially-corresponding representations Marker provides in
parallel — one (the `<table>` HTML) has correct logical structure but no per-cell
geometry, the other (`TableCell` children) has per-cell geometry but no row/column
index. Forcing them into a single type would require either fabricating row/column
indices on the geometry side (an unverified bbox-clustering reconstruction the
findings explicitly flagged as risky) or discarding per-cell geometry on the logical
side (losing the evidence-highlighting capability entirely). Keeping them separate,
each true to what Marker actually provides, is the choice that adds no
unverified inference. **Open implementation note, not a schema decision:**
positionally correlating a given `TableRowCell` with its corresponding `TableCell`
(for evidence highlighting of a specific logical cell) is left to the Normalizer to
attempt via parse-order correspondence; this spec does not assert that
correspondence is guaranteed, since it was not empirically verified.

---

## 13. Figure

**Purpose.** A figure region, with its caption normalized the same way as `Table`.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the Figure block's id]` (and `FigureGroup` id, if present). |
| `caption` | Optional[`Caption`] | no | Marker-observed | Section 11. Empirically, `FigureGroup` always pairs `[Figure, Caption]` in that order (mirroring `TableGroup`'s pairing, just with reversed order — confirmed, not assumed, per the findings doc). |
| `image_data` | Optional[bytes] | no | Marker-observed | Base64-decoded raster image content from Marker's `images` field, when present. Empirically, in the representative paper, only `Picture` blocks (journal logo, cover thumbnail) carried non-empty `images`; the one `Figure` block had `images: {}`. This field is therefore included (figures plausibly can carry raster data, and the project must not assume they never will) but its emptiness in the current evidence base is recorded explicitly in Section 22 as unconfirmed, not silently assumed resolved. |

---

## 14. Equation

**Purpose.** A mathematical expression block.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the Equation block's id]`. |
| `raw_math` | str | yes | Marker-observed | The verbatim MathML-ish `<math>` content, including any equation number embedded inline (e.g. `"DP = I - IR + P - ETc \pm VR, \qquad (1)"`), per empirical finding 3.7. |
| `equation_number` | Optional[str] | no | Architectural requirement (deferred) | A slot for the parsed-out equation number (e.g. `"1"`), since finding 3.7 confirmed Marker provides no separate field for it — any cross-reference resolution ("using equation (1)" in body text) requires parsing it out of `raw_math`. The parsing logic itself is out of scope for this spec; the field exists so its result has a defined home. |

---

## 15. Footnote

**Purpose.** A footnote block, with its attachment to a table or figure resolved
geometrically rather than structurally, per empirical finding 3.2.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the Footnote block's id]`. Note: this block's own provenance never implies attachment — footnotes are flat page-level siblings, not children of any Table/Figure (finding 3.2), so attachment is recorded separately below. |
| `raw_text` | str | yes | Marker-observed | Verbatim footnote content. |
| `attached_object_id` | Optional[str] | no | Architectural requirement (deferred) | The id of the `Table` or `Figure` this footnote was determined to belong to, via the Normalizer's bbox-proximity heuristic ("nearest preceding Table/Figure on the same page by bbox y-position," per finding 3.2). `None` when unresolved — tracked in aggregate by `Statistics.unresolved_footnote_count` (Section 7). The heuristic itself is Normalizer logic, out of scope here; the field exists so its output, including the legitimate possibility of non-resolution, has a defined, queryable home. |

**Why attachment is nullable rather than required.** Forcing every footnote to
resolve to a table/figure would hide genuine ambiguity (e.g. a footnote whose
geometric position is equidistant between two candidates, or a page-level
disclaimer footnote unrelated to any table) behind an incorrect best-guess. Per the
project's broader principle (already established for the IR: "fields that cannot be
resolved are marked with an unresolved status rather than silently filled"), the
same discipline applies at the structural layer: `None` is a legitimate, recorded
outcome, not an implementation gap to paper over.

---

## 16. Reference (Bibliography Entry)

**Purpose.** One bibliography entry, structurally distinguished from body text
because Marker represents references via `ListGroup`/`ListItem`, not `Text` blocks
(observed directly in the page_stats/structure walkthrough, not inferred from
content).

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the ListItem block's id]`. |
| `raw_text` | str | yes | Marker-observed | Verbatim reference entry text, including any inline markup Marker preserved. |

**Boundary note.** Like `Metadata` (Section 5), `Reference` deliberately stops at
verbatim text. Parsing a reference string into author/year/journal/DOI fields is
citation-matching — a semantic operation belonging to the IR's `Citation` entity,
not this layer. This object's only job is to say "this `ListItem`, structurally,
is a bibliography entry, not body text," which is information Marker's block typing
already gives for free via the `ListGroup` container.

---

## 17. PageHeader / PageFooter

**Purpose.** Repeated journal running-header/footer content (e.g. the journal name
repeated on every page, or page-footer branding), retained for completeness and
front-matter heuristics (Section 8) but not expected to be consumed by extraction.

| Field | Type | Required | Origin | Notes |
|---|---|---|---|---|
| `id` | str | yes | Architectural requirement | Per Section 2. |
| `provenance` | `StructuralProvenance` | yes | Marker-observed | `marker_block_ids = [the PageHeader/PageFooter block's id]`. |
| `raw_text` | str | yes | Marker-observed | Verbatim content. |

Modeled as two distinct types (`PageHeader`, `PageFooter`) rather than one generic
"running content" type, simply mirroring Marker's own distinct block types
one-to-one — there is no structural reason to merge them, and merging would lose
the type distinction Marker itself already makes.

---

## 18. Cross-Object Relationships & Invariants Summary

This section consolidates relationship rules stated piecemeal above, for a single
point of reference.

- **Containment is exclusively via `children` lists and explicit id-reference
  fields (`footnote_ids`, `attached_object_id`) — never via implicit ordering
  conventions or id-string parsing.** Any consumer needing "what footnotes belong
  to this table" reads `Table.footnote_ids`, never re-derives it from geometry
  itself; the Normalizer computes that relationship exactly once.
- **Reading order is a single global property (Section 3.4), independent of any
  per-object containment.** Two sibling objects under different `Section`s can be
  compared for relative reading order via their `reading_order_index` without
  needing to know anything about section nesting.
- **Every non-`Document` object carries exactly one `StructuralProvenance`,** which
  is the only place Marker block ids appear outside of `ProcessingMetadata`'s
  artifact reference. No object duplicates Marker ids elsewhere in its own fields.
- **No object type defined in this specification has a field referencing an IR,
  retrieval, validation, or export concept**, satisfying invariant 1.6 by
  construction — this is checked by inspection of this document, not by a runtime
  rule, since it is a closed schema with a fixed object list.

---

## 19. Serialization Requirements

- All models use `model_config = ConfigDict(frozen=True, extra="forbid")`. Unlike
  the Raw Marker Model (which intentionally used `extra="allow"` for forward
  compatibility with unknown future Marker fields), the Document Object is the project's own
  designed contract — an unexpected extra field here indicates a Normalizer bug,
  not a benign future Marker addition, so it should fail loudly (`extra="forbid"`)
  rather than silently passing through.
- `model_dump_json()` must be deterministic for a given object graph: field order
  follows declaration order (Pydantic v2 default), list order follows the
  semantically meaningful order already specified per field (reading order for
  children, left-to-right for table cells, outermost-to-innermost for
  `section_path`) — never a non-deterministic order like dict-hash order.
  `datetime` fields serialize as ISO 8601 strings in UTC.
- Every model must round-trip losslessly through `model_dump()` →
  `model_validate()` and `model_dump_json()` → `model_validate_json()`, mirroring
  the test discipline already established and passing for the Raw Marker Model.
- Bytes fields (`Figure.image_data`) serialize as base64 strings in JSON, matching
  Marker's own convention for `images`, so no separate encoding scheme is
  introduced at this layer.

---

## 20. Validation Rules

These are construction-time invariants enforced by each model's own validators,
distinct from the cross-cutting invariants in Section 1 (which are policies the
Normalizer must follow, not all individually mechanically checkable).

- `BoundingBox`: `x1 >= x0` and `y1 >= y0`.
- `StructuralProvenance`: `marker_block_ids` has at least one element;
  `reading_order_index >= 0`; exactly one of `bbox` or `contributing_bboxes` (or
  neither, for objects with genuinely no recoverable geometry) is populated — never
  both, to avoid two disagreeing geometric claims about the same object.
- `Document`: `pages` non-empty; `page_number` values across `pages` are unique.
- `Page`: `page_number >= 0`.
- `Table`: if `rows` is non-empty, every `TableRow.cells` list has at least one
  element (a row with zero cells is not a meaningful row — such input indicates a
  parse error in `raw_html`, which should surface as a Normalizer-time error, not a
  silently-accepted empty row in the Document Object).
- `Footnote`: no validation forces `attached_object_id` to be set — its absence is
  valid by design (Section 15).
- `Statistics`: every count field is `>= 0`; `unresolved_footnote_count <=
  footnote_count` (a basic sanity bound the model itself can check independent of
  whatever produced the numbers).

---

## 21. Explicitly Deferred — Not Modeled, By Design

Per the instruction to avoid speculative fields, the following structural cases
identified during evaluation are **intentionally absent** from this schema rather
than represented with a guessed-at field shape, because the representative paper
set does not yet provide enough evidence to know what shape is correct:

- **Multi-page table continuation.** Not observed in the representative paper (no
  table spans a page break). No `continues_on_page` / `continuation_of_table_id`
  field is added speculatively. When a representative paper exhibiting this is
  evaluated, this section is where such a field would be added — as an addition,
  not a redesign, since `Table` already has a stable `id` to reference.
- **Multi-panel figure decomposition.** The representative paper's Figure 3 has 10
  visually lettered sub-panels under one shared caption, but Marker recorded it as
  a single flat `Figure` block with no internal panel structure. Since this is the
  only data point (n=1) and it shows Marker *not* decomposing panels, no `panels:
  list[FigurePanel]` field is added on the strength of a PDF-visual observation that
  contradicts what Marker itself outputs. If a future paper shows Marker does
  sometimes decompose panels, this is where that field would be introduced.
- **TableGroup-vs-bare-Table triggering condition.** Both patterns are modeled
  (via `Caption`'s flexible provenance, Section 11), but *why* Marker chooses one
  over the other (single table per region vs. dense multi-table page, per the one
  data point available) is not encoded as a schema concept — it doesn't need to be,
  since the Document Object normalizes both outcomes into the same `Caption` shape
  regardless of cause.
- **Merged-cell reconstruction heuristic.** The *slot* (`TableRowCell.structural_
  notes`) exists (Section 12.2), but the specific rule for populating it (e.g.
  "empty cell directly below a filled cell in the same column ⇒ merged-placeholder
  suspected") is explicitly not decided here, per finding 3.4's own conclusion that
  this needs more representative papers first.

---

## 22. Summary — Field Origin Distribution

A consolidated view of the distinction requested for this specification: how many
fields per object are direct Marker carry-overs versus existing purely to satisfy
an architectural requirement (provenance, determinism, reproducibility,
serialization) versus reserved as a deferred-population slot for a Normalizer
heuristic not yet designed.

| Object | Marker-observed fields | Architectural-requirement fields | Deferred-population slots |
|---|---|---|---|
| Document | `pages` | `id`, `source_pdf_identifier`, `metadata`, `processing_metadata`, `statistics` | — |
| Metadata | `title`, `page_count`, `has_front_matter_page` | — | — |
| ProcessingMetadata | `marker_version` | `normalizer_version`, `processed_at`, `source_marker_artifact_ref` | — |
| Statistics | — | all count fields | — |
| Page | `page_number`, `children`, `is_front_matter` (heuristic) | `id`, `provenance` | — |
| Section | `heading_text`, `depth`, `children` | `id`, `provenance` | — |
| Paragraph | `text` | `id`, `provenance` | — |
| Caption | `label`, `text`, `trailing_notes` | `provenance` | — |
| Table | `raw_html`, `rows`, `cells`, `caption` | `id`, `provenance` | `footnote_ids` |
| TableRowCell | `text`, `is_header` | — | `structural_notes` |
| TableCell | `text`, `bbox`, `polygon` | `id` | — |
| Figure | `caption`, `image_data` | `id`, `provenance` | — |
| Equation | `raw_math` | `id`, `provenance` | `equation_number` |
| Footnote | `raw_text` | `id`, `provenance` | `attached_object_id` |
| Reference | `raw_text` | `id`, `provenance` | — |
| PageHeader/PageFooter | `raw_text` | `id`, `provenance` | — |

---

## 23. Exit Criteria for This Specification

This specification is ready to be frozen and handed to implementation once:

1. Every object above has a 1:1 or many:1 mapping back to either an observed
   Marker block type or a named architectural requirement (satisfied throughout
   this document via the "Origin" column on every field table).
2. No field exists whose justification is "might be useful later" rather than
   "Marker provides this" or "the architecture requires this for provenance /
   determinism / reproducibility / serialization / validation" (satisfied; the one
   category that looks speculative — deferred-population slots — is explicitly
   justified by the stated requirement to avoid future schema redesign, and is
   listed exhaustively in Section 22's third column plus Section 21's explicit
   exclusions).
3. No object or field encodes scientific meaning (satisfied — verified against
   invariant 1.2 by inspection of the full object list in Sections 4–17).
4. Implementing this specification in Pydantic v2 requires translation, not new
   design decisions — the identifier rule (Section 2), provenance rule (Section
   3.3), reading-order rule (Section 3.4), and every per-object field table are
   concrete enough to type directly.

Once reviewed and approved, the next phase is the mechanical translation of this
document into immutable Pydantic v2 models, followed by the Normalizer that
populates them from the Raw Marker Model.
