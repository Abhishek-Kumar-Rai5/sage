"""
components/unresolved.py
================
Dedicated page listing every field currently marked UNRESOLVED across all
entity types. Frames unresolved state as an intentional human-review
checkpoint, not a system failure.
"""

import streamlit as st
import state
import styles
from components import provenance


def render():
    st.subheader("Unresolved Items")
    st.caption(
        "These are fields the system could not confidently extract or attribute. "
        "This is an expected part of the review process — not necessarily a "
        "system failure. Resolve them here or leave them unresolved for now."
    )
    st.markdown("---")

    unresolved_items = []
    for entity_type, records in st.session_state.records.items():
        for rec in records:
            for field_name, field in rec["fields"].items():
                if field.get("status") == "UNRESOLVED":
                    unresolved_items.append((entity_type, rec, field_name, field))

    if not unresolved_items:
        st.success("No unresolved items remain. The dataset is clear for final review.")
        return

    if st.session_state.get("last_action_message"):
        st.success(st.session_state.last_action_message)
        st.session_state.last_action_message = None

    for entity_type, rec, field_name, field in unresolved_items:
        key_prefix = f"unresolved_{entity_type}_{rec['id']}_{field_name}"
        with st.container(border=True):
            st.markdown(
                f"**{rec['entity_type']}.{field_name}**  "
                f"&nbsp; `{rec['id']}`"
            )
            st.markdown(styles.status_badge("UNRESOLVED"), unsafe_allow_html=True)
            st.caption(f"Reason: {field.get('reason') or 'No reason provided.'}")

            if rec.get("evidence"):
                st.markdown("Evidence examined:")
                provenance.render_source_link(rec["evidence"], key_prefix)

            st.markdown("")
            resolve_col, keep_col = st.columns(2)
            with resolve_col:
                with st.popover("Resolve", use_container_width=True):
                    new_val = st.text_input(
                        "Enter resolved value", key=f"{key_prefix}_resolve_input")
                    if st.button("Confirm resolve", key=f"{key_prefix}_confirm"):
                        if new_val.strip():
                            state.resolve_field(entity_type, rec["id"], field_name, new_val.strip())
                            st.rerun()
                        else:
                            st.warning("Enter a value before resolving.")
            with keep_col:
                if st.button("Keep unresolved", key=f"{key_prefix}_keep", use_container_width=True):
                    state.keep_unresolved(entity_type, rec["id"], field_name)
                    st.rerun()