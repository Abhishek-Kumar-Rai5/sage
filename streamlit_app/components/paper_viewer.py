"""
components/paper_viewer.py
================
The "Open in paper" side-by-side review view.

LEFT  : the extracted record/value, field status, confidence/inference
        info, source anchor(s) (with a selector when there's more than
        one), and review actions (Accept / Reject / Edit-in-list).
RIGHT : the original PDF, auto-navigated to the provenance page, with the
        exact source polygon highlighted (components/pdf_viewer.py).

This view is reached via state.open_in_paper(...) (see components/
provenance.py), which stashes the (entity_type, record_id, field_name,
anchors) context in st.session_state.paper_review. It is not a normal
sidebar destination - app.py routes to it whenever
st.session_state.nav == state.PAPER_REVIEW_NAV.
"""

import streamlit as st
import api_client
import state
import styles
from components import pdf_viewer
from components.record_viewer import _label

PDF_VIEWER_HEIGHT = 640


def render():
    pr = st.session_state.paper_review
    if not pr:
        st.info("No record selected. Go back and choose \u201cOpen in paper\u201d on a field.")
        if st.button("Back"):
            state.close_paper_review()
            st.rerun()
        return

    entity_type = pr["entity_type"]
    record_id = pr["record_id"]
    field_name = pr["field_name"]
    anchors = pr["anchors"]
    active_anchor = pr["active_anchor"]

    record = state.get_record(entity_type, record_id)

    header_col, close_col = st.columns([0.82, 0.18])
    with header_col:
        st.subheader("Provenance Review")
        subtitle = f"{entity_type.capitalize()} \u00b7 `{record_id}`"
        if field_name:
            subtitle += f" \u00b7 field `{field_name}`"
        st.caption(subtitle)
    with close_col:
        st.markdown("<div style='padding-top:1.6rem;'></div>", unsafe_allow_html=True)
        if st.button("\u2715 Close", key="paper_review_close", use_container_width=True):
            state.close_paper_review()
            st.rerun()

    if not record:
        st.error("This record could no longer be found (it may have been removed).")
        return

    st.markdown("---")
    left, right = st.columns([0.42, 0.58], gap="large")

    with left:
        _render_left_panel(entity_type, record, field_name, anchors, active_anchor)

    with right:
        _render_right_panel(active_anchor)


def _render_left_panel(entity_type, record, field_name, anchors, active_anchor):
    rec_id = record["id"]

    status_row = st.columns([0.55, 0.45])
    with status_row[0]:
        st.markdown(f"**{record['entity_type']}** record")
    with status_row[1]:
        st.markdown(
            f'<div style="text-align:right;">{styles.status_badge(record["review_status"])}</div>',
            unsafe_allow_html=True,
        )

    meta_bits = []
    if record.get("confidence") is not None:
        meta_bits.append(f"Confidence: **{record['confidence']:.0%}**")
    if record.get("inference_source"):
        meta_bits.append(f"Source: *{record['inference_source']}*")
    if meta_bits:
        st.caption(" &nbsp;\u00b7&nbsp; ".join(meta_bits))

    st.markdown("")
    st.markdown("**Extracted value**")

    fields_to_show = {field_name: record["fields"][field_name]} if field_name and field_name in record["fields"] \
        else record["fields"]

    for f_name, field in fields_to_show.items():
        value = field["value"]
        st.markdown(
            f'<div class="field-card">'
            f'<div class="field-label">{_label(f_name)}</div>'
            f'<div class="field-value">{value if value not in (None, "") else "\u2014"}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        status = field.get("status", "EXTRACTED")
        st.markdown(styles.status_badge(status), unsafe_allow_html=True)
        if status == "UNRESOLVED" and field.get("reason"):
            st.caption(f"Reason: {field['reason']}")

    st.markdown("")
    st.markdown("**Source anchor(s)**")
    if len(anchors) > 1:
        st.caption("This record has multiple evidence anchors — choose which one to view.")
        selected = st.radio(
            "Source anchor", options=anchors,
            index=anchors.index(active_anchor) if active_anchor in anchors else 0,
            format_func=lambda a: f"\u27e6{a}\u27e7",
            key=f"anchor_radio_{rec_id}_{field_name}",
            label_visibility="collapsed",
        )
        if selected != active_anchor:
            state.set_active_provenance_anchor(selected)
            st.rerun()
    else:
        st.markdown(styles.anchor_tag(anchors[0]), unsafe_allow_html=True)

    st.markdown("")
    st.markdown("**Review actions**")
    a1, a2 = st.columns(2)
    if a1.button("Accept", key="paper_review_accept", use_container_width=True):
        state.set_record_status(entity_type, rec_id, "ACCEPTED")
        st.rerun()
    if a2.button("Reject", key="paper_review_reject", use_container_width=True):
        state.set_record_status(entity_type, rec_id, "REJECTED")
        st.rerun()
    if st.button("Edit this record", key="paper_review_edit", use_container_width=True):
        return_nav = st.session_state.get("_paper_review_return_nav", "Overview")
        state.close_paper_review()
        state.start_editing(entity_type, rec_id)
        # start_editing needs the record's own review page to be active.
        nav_label = None
        import mock_data
        for label, et in {
            "Citation": "citation", "Studies": "study", "Sites": "site",
            "Treatments": "treatment", "Observations": "observation",
            "Management": "management",
        }.items():
            if et == entity_type:
                nav_label = label
        state.navigate(nav_label or return_nav)
        st.rerun()


def _render_right_panel(active_anchor: str):
    block = state.get_document_block(active_anchor)
    if not block:
        st.warning(f"No provenance geometry found for \u27e6{active_anchor}\u27e7.")
        return
    if block.get("page") is None or block.get("polygon") is None:
        st.warning(
            f"\u27e6{active_anchor}\u27e7 has no page/polygon geometry yet — showing the "
            "extracted block text instead."
        )
        st.markdown(
            f'<div class="field-card">{block["text"]}</div>', unsafe_allow_html=True
        )
        return

    pdf_bytes = api_client.get_pdf_bytes(st.session_state.paper_id)
    pdf_viewer.render_pdf_page(
        pdf_bytes=pdf_bytes,
        page_number=block["page"],
        polygon=block["polygon"],
        block_id=active_anchor,
        height=PDF_VIEWER_HEIGHT,
        key=f"paper_pdf_{active_anchor}",
    )
    st.caption(
        "Highlighted region is the exact source block for this anchor, computed from "
        "stored page + polygon provenance data — not a text search."
    )