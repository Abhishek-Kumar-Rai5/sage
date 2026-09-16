"""
components/document_viewer.py
================
Renders the mock parsed-document view with visible provenance anchors
(⟦b:XXXX⟧). Not a PDF viewer - just a readable block list, which is
enough for the scientist to confirm where a value came from.
"""

import streamlit as st
import state
import styles


def render():
    st.subheader("Document")
    paper = st.session_state.document["paper"]
    st.caption(f"Parsed source blocks for: {paper['title']}")

    blocks = st.session_state.document["blocks"]

    highlight = st.session_state.selected_anchor

    for block in blocks:
        anchor = block["anchor"]
        is_selected = anchor == highlight
        border_color = "#0b5fff" if is_selected else "#e3e6ea"
        bg = "#eef4ff" if is_selected else "#ffffff"

        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            st.markdown(
                f'<div style="border:1px solid {border_color};background:{bg};'
                f'border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.4rem;">'
                f'{styles.anchor_tag(anchor)}'
                f'<div style="margin-top:6px;white-space:pre-wrap;">{block["text"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("Select", key=f"select_{anchor}", use_container_width=True):
                state.select_anchor(anchor)
                st.rerun()

    st.markdown("---")
    st.caption(
        "This is a mock rendering of parsed document blocks standing in for the "
        "real Marker output. Anchors (⟦b:XXXX⟧) are provenance references used "
        "throughout the review UI."
    )