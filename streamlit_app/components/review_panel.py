"""
components/review_panel.py
================
Entity-type page shell: header, short explanation, progress line, then a
list of records rendered through the shared record_viewer component.
Used identically for Citation, Study, Site, Treatment, Observation, and
Management so the relationships between entities stay visually
consistent.
"""

import streamlit as st
import state
import mock_data
from components import record_viewer


def render(entity_type: str):
    label = mock_data.ENTITY_LABELS[entity_type]
    records = state.get_records(entity_type)

    st.subheader(label)
    st.caption(
        "The system proposes these records from the document. You have final "
        "authority: accept, edit, or reject each one."
    )

    summary = state.review_summary()[entity_type]
    st.markdown(
        f"**{summary['total']}** records &nbsp;·&nbsp; "
        f"**{summary['reviewed']}** reviewed &nbsp;·&nbsp; "
        f"**{summary['unresolved']}** unresolved"
    )
    st.markdown("---")

    if not records:
        st.info(f"No {label.lower()} records in this mock dataset.")
        return

    if st.session_state.get("last_action_message"):
        st.success(st.session_state.last_action_message)
        st.session_state.last_action_message = None

    for record in records:
        record_viewer.render_record(entity_type, record)