"""Tests for Section (Spec Section 9) and Page (Spec Section 8), with
specific focus on the Version 1.1 correction:
"""
from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from betydb_extraction.document import (
    NodeKind,
    Page,
    PageChild,
    Paragraph,
    Reference,
    Section,
    SectionChild,
    Table,
)

from .conftest import (
    make_equation,
    make_figure,
    make_footnote,
    make_page,
    make_page_footer,
    make_page_header,
    make_paragraph,
    make_provenance,
    make_reference,
    make_section,
    make_table,
)


class TestSectionChildUnionIncludesReference:
    """The Version 1.1 correction, verified directly."""

    def test_reference_is_a_valid_section_child_by_direct_construction(self):
        ref = make_reference()
        section = make_section(
            heading_text="References",
            children=[ref],
        )
        assert len(section.children) == 1
        assert isinstance(section.children[0], Reference)
        assert section.children[0].kind == NodeKind.REFERENCE

    def test_section_with_mixed_children_including_reference(self):
        section = make_section(
            heading_text="References",
            children=[make_paragraph(), make_reference(), make_reference("/page/9/ListItem/1")],
        )
        kinds = [child.kind for child in section.children]
        assert kinds == [NodeKind.PARAGRAPH, NodeKind.REFERENCE, NodeKind.REFERENCE]

    def test_discriminated_union_resolves_reference_from_dict(self):
        # Simulates what happens when a Section is built from raw dict/JSON
        # data (e.g. round-tripped) -- the discriminator must correctly
        # route a 'reference' kind to the Reference model rather than
        # raising or silently coercing to a different type.
        ref = make_reference()
        section = Section(
            id=make_section().id,
            heading_text="References",
            provenance=make_provenance("/page/9/SectionHeader/0"),
            depth=0,
            children=[ref.model_dump()],
        )
        assert isinstance(section.children[0], Reference)

    def test_section_child_type_adapter_accepts_reference(self):
        adapter = TypeAdapter(SectionChild)
        ref = make_reference()
        resolved = adapter.validate_python(ref.model_dump())
        assert isinstance(resolved, Reference)

    def test_nested_sections_still_work_alongside_reference(self):
        inner = make_section(
            "/page/9/SectionHeader/1",
            heading_text="References",
            depth=1,
            children=[make_reference()],
        )
        outer = make_section(
            "/page/9/SectionHeader/0",
            heading_text="Back Matter",
            depth=0,
            children=[inner],
        )
        assert isinstance(outer.children[0], Section)
        assert isinstance(outer.children[0].children[0], Reference)

    def test_all_pre_v1_1_child_types_still_valid(self):
        # Guards against the v1.1 change accidentally narrowing the union
        # instead of only widening it.
        section = make_section(
            children=[
                make_paragraph(),
                make_table(),
                make_figure(),
                make_equation(),
                make_footnote(),
            ]
        )
        kinds = {child.kind for child in section.children}
        assert kinds == {
            NodeKind.PARAGRAPH,
            NodeKind.TABLE,
            NodeKind.FIGURE,
            NodeKind.EQUATION,
            NodeKind.FOOTNOTE,
        }


class TestPageChildUnionExcludesReference:

    def test_reference_is_not_in_page_child_union_members(self):
        adapter = TypeAdapter(PageChild)
        ref = make_reference()
        with pytest.raises(ValidationError):
            adapter.validate_python(ref.model_dump())

    def test_page_rejects_reference_as_direct_child(self):
        ref = make_reference()
        with pytest.raises(ValidationError):
            make_page(children=[ref])

    def test_page_accepts_section_header_footer_and_all_pre_v1_1_types(self):
        page = make_page(
            children=[
                make_page_header(),
                make_section(children=[make_paragraph()]),
                make_table(),
                make_figure(),
                make_equation(),
                make_footnote(),
                make_page_footer(),
            ]
        )
        assert len(page.children) == 7


class TestSection:
    def test_constructs_with_kind_default(self):
        section = make_section()
        assert section.kind == NodeKind.SECTION

    def test_children_default_to_empty_list(self):
        section = make_section()
        assert section.children == []

    def test_depth_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            make_section(depth=-1)

    def test_is_frozen(self):
        section = make_section()
        with pytest.raises(ValidationError):
            section.heading_text = "Different"

    def test_rejects_malformed_id(self):
        with pytest.raises(ValidationError):
            Section(
                id="not-an-id",
                heading_text="Methods",
                provenance=make_provenance(),
                depth=0,
            )


class TestPage:
    def test_page_number_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            make_page(page_number=-1)

    def test_children_default_to_empty_list(self):
        page = make_page()
        assert page.children == []

    def test_is_front_matter_required(self):
        with pytest.raises(ValidationError):
            Page(
                id=make_page().id,
                page_number=0,
                provenance=make_provenance("/page/0"),
                children=[],
            )

    def test_is_frozen(self):
        page = make_page()
        with pytest.raises(ValidationError):
            page.is_front_matter = True