"""Tests for the leaf and supporting content models: Paragraph, Caption,
Table (+ TableRow/TableRowCell/TableCell), Figure, Equation, Footnote,
Reference, PageHeader, PageFooter.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from betydb_extraction.document import (
    Caption,
    Equation,
    Figure,
    Footnote,
    NodeKind,
    PageFooter,
    PageHeader,
    Paragraph,
    Reference,
    Table,
    TableRow,
    TableRowCell,
)

from .conftest import (
    make_caption,
    make_equation,
    make_footnote,
    make_id,
    make_page_footer,
    make_page_header,
    make_paragraph,
    make_provenance,
    make_reference,
    make_table,
)


class TestParagraph:
    def test_constructs_with_kind_default(self):
        p = make_paragraph()
        assert p.kind == NodeKind.PARAGRAPH

    def test_preserves_inline_html_verbatim(self):
        p = make_paragraph(text="See <b>Table 3</b> for details.")
        assert p.text == "See <b>Table 3</b> for details."

    def test_rejects_malformed_id(self):
        with pytest.raises(ValidationError):
            Paragraph(id="not-an-id", text="x", provenance=make_provenance())

    def test_is_frozen(self):
        p = make_paragraph()
        with pytest.raises(ValidationError):
            p.text = "different"


class TestCaption:
    def test_all_text_fields_optional(self):
        cap = Caption(provenance=make_provenance())
        assert cap.label is None
        assert cap.text is None
        assert cap.trailing_notes is None

    def test_pattern_a_shape(self):
        cap = make_caption()
        assert cap.label == "Table 3"
        assert cap.text is not None

    def test_has_no_kind_discriminator(self):
        # Caption is embedded only, never a children-union member.
        assert not hasattr(Caption, "model_fields") or "kind" not in Caption.model_fields


class TestTable:
    def test_constructs_with_kind_default(self):
        t = make_table()
        assert t.kind == NodeKind.TABLE

    def test_row_with_zero_cells_rejected(self):
        with pytest.raises(ValidationError):
            TableRow(cells=[])

    def test_rows_may_be_empty_list(self):
        t = Table(
            id=make_id("/page/6/Table/1"),
            provenance=make_provenance("/page/6/Table/1"),
            raw_html="<table></table>",
        )
        assert t.rows == []

    def test_caption_optional(self):
        t = Table(
            id=make_id("/page/6/Table/2"),
            provenance=make_provenance("/page/6/Table/2"),
            raw_html="<table></table>",
        )
        assert t.caption is None

    def test_table_row_cell_math_stripped_text_is_plain_field(self):
        cell = TableRowCell(text="1.2 +/- 0.3", is_header=False)
        assert cell.text == "1.2 +/- 0.3"

    def test_table_row_cell_has_no_row_col_index_fields(self):
        assert "row_index" not in TableRowCell.model_fields
        assert "col_index" not in TableRowCell.model_fields

    def test_table_row_cell_has_no_span_fields(self):
        assert "rowspan" not in TableRowCell.model_fields
        assert "colspan" not in TableRowCell.model_fields


class TestFigure:
    def test_constructs_with_kind_default(self):
        from .conftest import make_figure

        fig = make_figure()
        assert fig.kind == NodeKind.FIGURE

    def test_image_data_optional(self):
        fig = Figure(
            id=make_id("/page/7/Figure/1"),
            provenance=make_provenance("/page/7/Figure/1"),
        )
        assert fig.image_data is None


class TestEquation:
    def test_constructs_with_kind_default(self):
        eq = make_equation()
        assert eq.kind == NodeKind.EQUATION

    def test_equation_number_is_separate_optional_slot(self):
        eq = Equation(
            id=make_id("/page/3/Equation/1"),
            provenance=make_provenance("/page/3/Equation/1"),
            raw_math="<math>E = mc^2</math>",
            equation_number="2",
        )
        assert eq.equation_number == "2"
        assert "(2)" not in eq.raw_math  # number is a separate field here

    def test_raw_math_can_embed_number_inline(self):
        # Per spec: Marker provides no separate field, so raw_math may
        # contain the number embedded in the string itself.
        eq = Equation(
            id=make_id("/page/3/Equation/2"),
            provenance=make_provenance("/page/3/Equation/2"),
            raw_math="<math>y = mx + b ... (1)</math>",
        )
        assert "(1)" in eq.raw_math
        assert eq.equation_number is None


class TestFootnote:
    def test_constructs_with_kind_default(self):
        fn = make_footnote()
        assert fn.kind == NodeKind.FOOTNOTE

    def test_attached_object_id_defaults_to_none(self):
        fn = make_footnote()
        assert fn.attached_object_id is None

    def test_unresolved_attachment_does_not_fail_validation(self):
        # Spec 20: no validation forces attached_object_id to be set.
        fn = Footnote(
            id=make_id("/page/0/Footnote/1"),
            provenance=make_provenance("/page/0/Footnote/1"),
            raw_text="2. Another note.",
            attached_object_id=None,
        )
        assert fn.attached_object_id is None

    def test_attached_object_id_can_be_set(self):
        fn = Footnote(
            id=make_id("/page/0/Footnote/2"),
            provenance=make_provenance("/page/0/Footnote/2"),
            raw_text="3. Yet another.",
            attached_object_id=make_id("/page/0/Table/0"),
        )
        assert fn.attached_object_id is not None


class TestReference:
    """Reference per Spec Section 16, Version 1.1 (kind discriminator added)."""

    def test_constructs_with_kind_default(self):
        ref = make_reference()
        assert ref.kind == NodeKind.REFERENCE

    def test_kind_is_required_in_field_set(self):
        assert "kind" in Reference.model_fields

    def test_raw_text_preserved_verbatim(self):
        ref = make_reference()
        assert "Smukler" in ref.raw_text

    def test_is_frozen(self):
        ref = make_reference()
        with pytest.raises(ValidationError):
            ref.raw_text = "different"

    def test_rejects_malformed_id(self):
        with pytest.raises(ValidationError):
            Reference(id="bad-id", provenance=make_provenance(), raw_text="x")


class TestPageHeaderFooter:
    def test_page_header_constructs_with_kind_default(self):
        h = make_page_header()
        assert h.kind == NodeKind.PAGE_HEADER

    def test_page_footer_constructs_with_kind_default(self):
        f = make_page_footer()
        assert f.kind == NodeKind.PAGE_FOOTER

    def test_distinct_types_not_merged(self):
        assert PageHeader is not PageFooter
        assert PageHeader.model_fields["kind"].default != PageFooter.model_fields["kind"].default