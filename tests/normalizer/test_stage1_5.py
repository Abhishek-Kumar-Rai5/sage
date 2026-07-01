"""Tests for Stage 1.5: Wrapper Unwrapping."""
from __future__ import annotations

from betydb_extraction.marker_adapter.raw_model import MarkerBlock
from betydb_extraction.normalizer.builders.base import UnwrappedBlock, WrapperContext
from betydb_extraction.normalizer.internal.stage1_5 import unwrap_page


def _block(block_id: str, block_type: str, children=None) -> MarkerBlock:
    return MarkerBlock(id=block_id, block_type=block_type, children=children)


def test_direct_non_wrapper_child_has_none_context():
    text = _block("/p/0/Text/0", "Text", children=None)
    result = unwrap_page([text])

    assert len(result) == 1
    assert result[0].block is text
    assert result[0].wrapper_context is None


def test_table_group_unwrapped_one_level():
    cell1 = _block("/p/0/TableCell/0", "TableCell", children=None)
    cell2 = _block("/p/0/TableCell/1", "TableCell", children=None)
    table_group = _block("/p/0/TableGroup/0", "TableGroup", children=[cell1, cell2])

    result = unwrap_page([table_group])

    assert len(result) == 2
    assert result[0].block is cell1
    assert result[1].block is cell2
    for r in result:
        assert r.wrapper_context == WrapperContext(
            wrapper_type="TableGroup", block_id="/p/0/TableGroup/0"
        )


def test_figure_group_unwrapped_one_level():
    pic = _block("/p/0/Picture/0", "Picture", children=None)
    figure_group = _block("/p/0/FigureGroup/0", "FigureGroup", children=[pic])

    result = unwrap_page([figure_group])

    assert len(result) == 1
    assert result[0].block is pic
    assert result[0].wrapper_context == WrapperContext(
        wrapper_type="FigureGroup", block_id="/p/0/FigureGroup/0"
    )


def test_list_group_unwrapped_one_level():
    item = _block("/p/0/ListItem/0", "ListItem", children=None)
    list_group = _block("/p/0/ListGroup/0", "ListGroup", children=[item])

    result = unwrap_page([list_group])

    assert len(result) == 1
    assert result[0].block is item
    assert result[0].wrapper_context == WrapperContext(
        wrapper_type="ListGroup", block_id="/p/0/ListGroup/0"
    )


def test_nested_wrapper_not_recursively_unwrapped():
    inner_list_group = _block(
        "/p/0/ListGroup/0", "ListGroup",
        children=[_block("/p/0/ListItem/0", "ListItem", children=None)],
    )
    outer_table_group = _block(
        "/p/0/TableGroup/0", "TableGroup", children=[inner_list_group]
    )

    result = unwrap_page([outer_table_group])

    assert len(result) == 1
    assert result[0].block is inner_list_group
    assert result[0].block.block_type == "ListGroup"
    assert result[0].wrapper_context == WrapperContext(
        wrapper_type="TableGroup", block_id="/p/0/TableGroup/0"
    )


def test_order_preserved_across_mixed_blocks():
    text1 = _block("/p/0/Text/0", "Text", children=None)
    cell = _block("/p/0/TableCell/0", "TableCell", children=None)
    table_group = _block("/p/0/TableGroup/0", "TableGroup", children=[cell])
    text2 = _block("/p/0/Text/1", "Text", children=None)

    result = unwrap_page([text1, table_group, text2])

    assert [r.block for r in result] == [text1, cell, text2]
    assert result[0].wrapper_context is None
    assert result[1].wrapper_context is not None
    assert result[2].wrapper_context is None


def test_wrapper_with_empty_children_contributes_nothing():
    empty_group = _block("/p/0/TableGroup/0", "TableGroup", children=[])
    text = _block("/p/0/Text/0", "Text", children=None)

    result = unwrap_page([empty_group, text])

    assert len(result) == 1
    assert result[0].block is text


def test_empty_page_returns_empty_list():
    assert unwrap_page([]) == []


def test_original_list_not_mutated():
    text = _block("/p/0/Text/0", "Text", children=None)
    children = [text]
    original_len = len(children)

    unwrap_page(children)

    assert len(children) == original_len
    assert children[0] is text


def test_return_type_is_unwrapped_block():
    text = _block("/p/0/Text/0", "Text", children=None)
    result = unwrap_page([text])
    assert isinstance(result[0], UnwrappedBlock)