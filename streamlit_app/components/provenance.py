"""
components/provenance.py
================
Reusable "where did this come from?" panel. Given one or more anchors,
shows the corresponding mock document block(s) inline so the scientist
never has to leave the review screen to check provenance.
"""

import streamlit as st
import state
import styles


def render_source_link(anchors: list[str], key_prefix: str):
    """Render anchor tags + a 'View source' button. Call render_source_panel
    right after this, guarded by the same key, to actually show the block."""
    if not anchors:
        st.caption("No source anchors available.")
        return

    tags_html = " ".join(styles.anchor_tag(a) for a in anchors)
    st.markdown(f"Source: {tags_html}", unsafe_allow_html=True)

    view_key = f"view_source_{key_prefix}"
    if st.button("View source", key=view_key):
        st.session_state[f"_show_provenance_{key_prefix}"] = True
        state.select_anchor(anchors[0])

    if st.session_state.get(f"_show_provenance_{key_prefix}"):
        render_source_panel(anchors, key_prefix)


def render_source_panel(anchors: list[str], key_prefix: str):
    with st.container(border=True):
        st.markdown("**Provenance — source block(s)**")
        for anchor in anchors:
            block = state.get_document_block(anchor)
            if block:
                st.markdown(
                    f'{styles.anchor_tag(anchor)}'
                    f'<div style="margin-top:4px;white-space:pre-wrap;">{block["text"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("")
            else:
                st.caption(f"⟦{anchor}⟧ — block not found in mock document.")
        if st.button("Hide source", key=f"hide_source_{key_prefix}"):
            st.session_state[f"_show_provenance_{key_prefix}"] = False
            st.rerun()