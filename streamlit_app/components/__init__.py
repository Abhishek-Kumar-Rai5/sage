"""
components package
================
UI components for the IR Scientist Review Streamlit prototype:
document_viewer, record_viewer, review_panel, provenance, unresolved.

Every module here talks only to state.py / styles.py -- never to
mock_data.py directly -- so the prototype stays decoupled from the
future FastAPI backend (see api_client.py).
"""