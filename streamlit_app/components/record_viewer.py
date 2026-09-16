"""
components/record_viewer.py
================
One reusable component for reviewing ANY record type (Citation, Study,
Site, Treatment, Observation, Management). This is intentional: the task
calls for a single consistent review pattern rather than a bespoke UI per
entity type.

Every record shows: entity type, record id, review status, fields
(value/status/source anchor), confidence, inference source, and actions
(Accept / Edit / Reject). Editing swaps into a Streamlit form; saving only
touches st.session_state via state.py.
"""

import streamlit as st
import state
import styles
from components import provenance

FIELD_LABELS_OVERRIDE = {
    "persistent_identifier": "Persistent Identifier",
}


def _label(field_name: str) -> str:
    if field_name in FIELD_LABELS_OVERRIDE:
        return FIELD_LABELS_OVERRIDE[field_name]
    return field_name.replace("_", " ").title()


def render_record(entity_type: str, record: dict):
    rec_id = record["id"]
    key_prefix = f"{entity_type}_{rec_id}"

    with st.container(border=True):
        header_col1, header_col2 = st.columns([0.7, 0.3])
        with header_col1:
            st.markdown(f"#### {record['entity_type']} · `{rec_id}`")
        with header_col2:
            st.markdown(
                f'<div style="text-align:right;padding-top:6px;">'
                f'{styles.status_badge(record["review_status"])}</div>',
                unsafe_allow_html=True,
            )

        meta_bits = []
        if record.get("confidence") is not None:
            meta_bits.append(f"Confidence: **{record['confidence']:.0%}**")
        if record.get("inference_source"):
            meta_bits.append(f"Source: *{record['inference_source']}*")
        if meta_bits:
            st.caption(" &nbsp;·&nbsp; ".join(meta_bits))

        st.markdown("")

        editing = state.is_editing(entity_type, rec_id)

        if editing:
            _render_edit_form(entity_type, record, key_prefix)
        else:
            _render_fields_readonly(entity_type, record, key_prefix)
            _render_actions(entity_type, record, key_prefix)


def _render_fields_readonly(entity_type: str, record: dict, key_prefix: str):
    for field_name, field in record["fields"].items():
        st.markdown(
            f'<div class="field-card">'
            f'<div class="field-label">{_label(field_name)}</div>'
            f'<div class="field-value">{field["value"] if field["value"] not in (None, "") else "—"}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        status = field.get("status", "EXTRACTED")
        st.markdown(styles.status_badge(status), unsafe_allow_html=True)

        if status == "UNRESOLVED":
            reason = field.get("reason") or "No reason provided."
            st.caption(f"Reason: {reason}")
        elif field.get("anchors"):
            provenance.render_source_link(field["anchors"], f"{key_prefix}_{field_name}")
        st.markdown("<hr/>", unsafe_allow_html=True)


def _render_edit_form(entity_type: str, record: dict, key_prefix: str):
    st.markdown("**Editing record**")
    new_values = {}
    with st.form(key=f"form_{key_prefix}"):
        for field_name, field in record["fields"].items():
            value = field["value"]
            label = _label(field_name)
            if isinstance(value, int):
                new_values[field_name] = st.number_input(label, value=value,
                                                           key=f"input_{key_prefix}_{field_name}")
            elif field_name in ("authors",) or (isinstance(value, str) and len(value) > 60):
                new_values[field_name] = st.text_area(
                    label, value=value or "", key=f"input_{key_prefix}_{field_name}")
            else:
                new_values[field_name] = st.text_input(
                    label, value="" if value is None else str(value),
                    key=f"input_{key_prefix}_{field_name}")

        save_col, cancel_col = st.columns(2)
        saved = save_col.form_submit_button("Save changes", use_container_width=True)
        cancelled = cancel_col.form_submit_button("Cancel", use_container_width=True)

    if saved:
        state.update_record_fields(entity_type, record["id"], new_values)
        state.stop_editing()
        st.rerun()
    if cancelled:
        state.stop_editing()
        st.rerun()


def _render_actions(entity_type: str, record: dict, key_prefix: str):
    rec_id = record["id"]
    c1, c2, c3 = st.columns(3)
    if c1.button("Accept", key=f"accept_{key_prefix}", use_container_width=True):
        state.set_record_status(entity_type, rec_id, "ACCEPTED")
        st.rerun()
    if c2.button("Edit", key=f"edit_{key_prefix}", use_container_width=True):
        state.start_editing(entity_type, rec_id)
        st.rerun()
    if c3.button("Reject", key=f"reject_{key_prefix}", use_container_width=True):
        state.set_record_status(entity_type, rec_id, "REJECTED")
        st.rerun()