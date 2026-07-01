# Marker Output — Empirical Findings (Paper 1: Nutrient Cycling, Smukler et al. 2012)

Source: `/mnt/user-data/uploads/1781681908897_Nutrient-cycling.json`
17 pages. Tree rooted at a single `Document` node.

## 1. Universal block envelope

Every node in the tree, container or leaf, shares the identical field set:

```
id                : str   e.g. "/page/7/Table/2"  (path-like, encodes page + type + local index)
block_type        : str   e.g. "Table", "Text", "Page", "Document"
html              : str   either real inline HTML content (leaf), or a manifest of
                           <content-ref src="..."> pointers to children (container)
polygon           : list  4 [x,y] corner points
bbox              : list  [x0, y0, x1, y1]
children          : list | None   nested block objects, or None for true leaves
section_hierarchy : dict  {depth_str: section_header_id} — governing heading path
images            : dict | None   base64 image data keyed by this block's own id
                           (populated only for Picture blocks in this paper; {} otherwise)
```

No block type adds extra fields beyond this envelope. This means the schema's base
`MarkerBlock` type can be a single shape; specialization happens through `block_type`
plus type-specific *interpretation* of `html`/`children`, not through extra fields.

## 2. Global block-type census (this paper)

| block_type    | count | notes |
|---------------|-------|-------|
| TableCell     | 781   | always leaf, always child of a Table |
| Text          | 105   | leaf; generic paragraph/caption-fragment/note |
| ListItem      | 81    | leaf; reference entries |
| PageFooter    | 49    | leaf; repeated journal footer per page |
| Page          | 17    | container; one per PDF page |
| SectionHeader | 13    | leaf; includes real section headers AND table/figure labels ("Table 3") |
| Caption       | 7     | leaf; only appears inside TableGroup/FigureGroup wrapping |
| Table         | 7     | container of TableCells; html also contains a parallel full `<table>` HTML repr |
| Figure        | 6     | leaf (no children); images field empty in this paper (no embedded raster found) |
| ListGroup     | 6     | container of ListItems (reference list chunks) |
| Footnote      | 5     | leaf; NOT nested under their related Table — flat page-level siblings |
| TableGroup    | 3     | container: always exactly [Caption, Table] in that order |
| Picture       | 2     | leaf; carries actual base64 raster in `images` (journal logo/cover thumbnail) |
| Document      | 1     | root |
| PageHeader    | 1     | leaf |
| FigureGroup   | 1     | container: always exactly [Figure, Caption] in that order |
| Equation      | 1     | leaf; html contains MathML-ish `<math>` with the equation number INLINE in the math string |

Note: `Span` and `Line`, which appeared in the `page_stats` summary block_counts,
do NOT appear anywhere in the actual tree. They are lower-level OCR primitives that
Marker collapses into the parent block's `html` string and does not expose as tree
nodes. The schema should not plan to consume Span/Line directly.

## 3. Confirmed structural patterns

### 3.1 Caption pairing is inconsistent across two different mechanisms

**Pattern A — wrapped (TableGroup / FigureGroup):**
`TableGroup` and `FigureGroup` are containers whose children are ALWAYS exactly
`[Caption, Table]` or `[Figure, Caption]` respectively (order differs!: caption comes
*before* Table in TableGroup, *after* Figure in FigureGroup). Caption is a single
block of html content.

**Pattern B — unwrapped (bare Table directly under Page):**
No TableGroup wrapper exists. Instead, caption information is split across TWO
separate sibling blocks immediately preceding the Table:
  - a `SectionHeader` containing only the label, e.g. `<h4>Table 3</h4>`
  - a `Text` block containing the full descriptive caption sentence
A trailing `Text` block ("Note: ...") may also follow the table — this is part of
the caption/footnote apparatus, not body text.

Confirmed on page 7 (Tables 3 and 4, both unwrapped) vs. pages 6/10/12 (wrapped).
**The Document Schema must normalize both patterns into one canonical Table.caption
field** — the Normalizer needs a rule: "if TableGroup, caption = the Caption child's
text; if bare Table, caption = nearest-preceding SectionHeader text + nearest text
block before the Table, concatenated."

### 3.2 Footnote-to-Table attachment requires geometric inference

Footnotes are NEVER nested inside their related Table, and are NOT reliably
ordered/numbered adjacent to it either. On page 7: Table 3 (id .../Table/2),
Table 4 (id .../Table/8), and three Footnotes (ids .../Footnote/4, /5, /10) are
all flat siblings of the Page.

The only reliable signal for attachment is **bbox y-coordinate ordering**:
Footnote/4 (y: 271–280) and Footnote/5 (y: 283–292) fall between Table 3's
"Note" text (y: 259–268) and Table 4's header (y: 342) → belong to Table 3.
Footnote/10 (y: 663–674) falls after Table 4's Note (y: 652–661) → belongs to Table 4.

**Required Normalizer rule:** assign each Footnote to the nearest preceding
Table/Figure on the same page by bbox y-position, not by id adjacency or tree
nesting (id adjacency is NOT reliable — see Footnote ids 4,5 vs Table id 2,
and Footnote id 10 vs Table id 8; the numbering interleaves with other blocks).

### 3.3 Tables carry two parallel, partially redundant representations

A `Table` block's own `html` field contains a COMPLETE, correctly nested
`<table><tbody><tr><th>...</tr><tr><td>...</td></tr>...</tbody></table>` structure
with correct logical row/column grouping.

Separately, the same Table also has N `TableCell` children, each with its own
bbox/polygon, but **no explicit row index or column index field** — row/column
membership is implicit and would need to be reconstructed by clustering bbox
y-ranges (rows) and x-ranges (columns) if cell-level geometry is needed.

**Schema decision needed:** does the Document Object's canonical Table representation
parse structure from the `html` (reliable logical structure, no per-cell geometry),
from the `TableCell` children (per-cell geometry, structure must be inferred), or
both (html for logical truth, TableCell bboxes for evidence-highlighting only)?
Recommendation to evaluate against more papers: treat `html` as the source of
truth for logical table structure (rows/cols/headers), and TableCell geometry as
supplementary evidence-location data only, since reconstructing rows/cols from
bbox clustering independently risks disagreeing with Marker's own html parse.

### 3.4 Merged/spanning cells are silently flattened, not marked

Table 3 in the source PDF has merged row labels (e.g. "Irrigated Y1" / "(South Field)"
spans two visual rows as one label). Marker's output html does NOT use `rowspan`;
instead it duplicates the row structure and leaves the second row's corresponding
cell empty (`<td></td>`). There is no flag distinguishing "genuinely empty cell"
from "this is a placeholder for a merged cell above." This is invisible information
loss unless the schema explicitly accounts for it.

**Open question for the Document Schema:** do we attempt to reconstruct rowspans
heuristically (empty cell directly below a filled cell in the same column = merged),
or do we accept Marker's flattening as-is and rely on the original row-group label
(e.g. "Irrigated Y1") being unambiguous from context alone? Needs testing against
more papers with merged cells before deciding — flagging as deferred per the
agreed scoping (don't over-design from one example).

### 3.5 Inline math/value formatting is inconsistent within the same table

Numerically identical value formats (`mean ± stderr`) appear sometimes as plain
text (`7.9 ± 0.1`) and sometimes wrapped in `<math>7.9 \pm 0.1</math>` within the
SAME table, seemingly depending on which OCR path (`pdftext` vs `surya`) produced
that specific cell. This matches the evaluation's noted concern about superscript/
subscript/symbol OCR artifacts.

**Required Normalizer rule:** strip/unwrap `<math>` tags during cell text
extraction and treat their content as equivalent plain text — do not let table
schema or downstream parsing branch on whether a cell happens to contain a
`<math>` wrapper.

### 3.6 Significance markers are embedded in cell text, not structured

Asterisks and daggers indicating statistical significance (`**`, `*`, `†`) are
appended directly to the numeric text inside table cells (e.g. `"64.5 ± 16.7**"`),
rather than being a separate, structured annotation. Linking a given cell's
significance marker to its meaning requires (a) parsing trailing marker characters
off the cell text, and (b) resolving them against the page's Footnote blocks
(per 3.2) which define what `*`, `**`, `†` mean for that table.

**Required IR/Evidence implication:** a Measurement object extracted from such
a cell needs a place to carry a `significance_annotation` (raw marker + resolved
meaning), sourced from combining the cell text parse with the resolved footnote.

### 3.7 Equation numbering is embedded in the math string, not a separate field

The single Equation block in this paper has html:
`<p block-type="Equation"><math display="block">DP = I - IR + P - ETc \pm VR, \qquad (1)</math></p>`

The `(1)` equation number is part of the math content string itself. There is no
separate `equation_number` field. Any cross-reference resolution (body text says
"using equation (1)") will need to parse the number out of the math string.

### 3.8 Front-matter / non-scientific content is structurally indistinguishable

Page 0 (journal cover/routing page — ISSN, "Submit your article," "Article views: 133",
Taylor & Francis branding) uses the exact same block types (Picture, SectionHeader,
Text, Figure, PageFooter) as genuine content pages. Nothing in block_type or
structure flags this page as non-scientific front matter — Marker has no concept
of "this entire page is publisher wrapper, not part of the paper." This must be
detected, if needed, by content heuristics (presence of "ISSN", "Submit your
article", DOI-only content, etc.) or simply accepted into the Document Object
and filtered downstream during scientific extraction (retrieval layer would
simply never retrieve it because it's not relevant to any scientific query).

### 3.9 `section_hierarchy` gives a live heading path per block

Every block carries a `section_hierarchy` dict mapping a depth-index string to
the id of the governing SectionHeader at that depth — e.g. a TableCell deep
inside Table 3 carries `{'1': '/page/1/SectionHeader/1', '4': '/page/7/SectionHeader/0'}`,
meaning "under top-level heading from page 1 (likely 'Materials and Methods'),
under nearer heading from page 7 ('Table 3')." This is effectively a precomputed
breadcrumb and is very useful — the Document Object's Section nesting can likely
be derived directly from this rather than re-deriving it from reading order.

## 4. Implications carried forward to Document Schema Specification

1. Base `MarkerBlock` envelope is uniform — confirms a single ingestion parser
   can handle all block types polymorphically by switching on `block_type`.
2. Table.caption must be normalized across two different Marker patterns (3.1).
3. Footnote attachment must be resolved by geometric proximity, not tree
   structure or id adjacency (3.2) — Normalizer needs explicit bbox-based rule.
4. Table logical structure should likely be sourced from `html`, not reconstructed
   from TableCell bboxes (3.3) — pending confirmation against more papers.
5. Merged-cell handling is an open/deferred question, not yet resolved (3.4).
6. `<math>` wrapper inconsistency must be normalized away at ingestion (3.5).
7. Significance markers need a dedicated annotation slot in the IR, sourced from
   combined cell-text-parsing + footnote-resolution (3.6).
8. Equation cross-references require number extraction from math string (3.7).
9. Front-matter detection is a content-heuristic problem, not structurally free (3.8).
10. `section_hierarchy` likely gives us Section nesting almost for free (3.9) —
    worth designing the Normalizer to lean on this rather than re-deriving nesting.

## 5. Still unverified / needs a second paper to confirm or refute

- Is TableGroup-wrapping vs bare-Table-with-SectionHeader purely a function of
  PDF layout (single table per region vs dense multi-table page), or something
  else? (Page 7 has 2 dense tables back-to-back and got the bare pattern; pages
  6/10/12 have one table each and got TableGroup.) Single-paper evidence only.
- Does Figure ever carry actual `images` data, or was the empty `images: {}` we
  saw specific to this paper's figures (which are likely vector/map graphics,
  not raster photos)? The only non-empty `images` we found were on the two
  Picture blocks (journal logo, cover thumbnail), not on any Figure block.
- Multi-page table continuation: NOT observed in this paper — no table spans
  a page break here. Still an open edge case requiring a different example paper.
- Multi-panel figures with one shared caption (e.g. Figure 3's panels a–j): the
  PDF clearly shows Figure 3 as 10 lettered sub-panels under one caption, but
  Marker recorded it as a single `Figure` block (id /page/8/Figure/...) with
  no internal panel structure. Need to confirm: does Marker ever decompose
  multi-panel figures, or does it always flatten to one Figure block regardless
  of internal panel count? This paper suggests always-flatten, but n=1.
