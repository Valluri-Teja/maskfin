"""
app.py
MaskFin: offline PII redaction + safe RAG chat over financial documents.

Four tabs:
- Redact: single-file, scan-then-review-then-confirm flow
- Batch: multiple files at once, auto-redacted (no per-item review -
  a stated tradeoff for throughput), zipped for download
- Chat: ask questions over the redacted document only
- History: persistent audit trail across sessions (labels/counts only,
  never the raw matched PII values - see history.py for why)

Run with: streamlit run app.py
"""

import os
import shutil
import pandas as pd
import streamlit as st

from detect import scan_document
from redact import apply_redactions
from compliance import get_citation
from chat_index import build_chat_index
from qa_chain import build_chain, ask, LLM_BACKEND
from history import log_session, get_all_sessions, get_session_items
from batch import process_batch, zip_results
from rate_limit import check_rate_limit, DEFAULT_LIMIT

st.set_page_config(page_title="MaskFin", layout="wide")
st.title("🛡️ MaskFin")
st.caption(
    f"Offline PII redaction for financial documents. PAN, Aadhaar, account "
    f"numbers, IFSC, GSTIN, passport, card, phone, and email are detected "
    f"locally — you review every match before anything is redacted. "
    f"LLM backend: **{LLM_BACKEND}**"
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "redacted"
INDEX_DIR = "chat_index"
BATCH_OUTPUT_DIR = "batch_redacted"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(BATCH_OUTPUT_DIR, exist_ok=True)

if "redaction_count" not in st.session_state:
    st.session_state.redaction_count = 0

tab_redact, tab_batch, tab_chat, tab_history = st.tabs(
    ["🖍️ Redact", "📦 Batch", "💬 Chat (redacted doc only)", "🕘 History"]
)

with tab_redact:
    st.caption(f"Session usage: {st.session_state.redaction_count}/{DEFAULT_LIMIT} redactions")
    uploaded = st.file_uploader("Upload a bank statement or ID document", type=["pdf", "jpg", "jpeg", "png"])

    if uploaded:
        input_path = os.path.join(UPLOAD_DIR, uploaded.name)
        with open(input_path, "wb") as f:
            f.write(uploaded.getbuffer())

        output_path = os.path.join(OUTPUT_DIR, f"redacted_{uploaded.name}")

        if st.button("Scan for PII"):
            with st.spinner("Running OCR and detecting PII locally..."):
                st.session_state.detections = scan_document(input_path)
                st.session_state.scanned_file = uploaded.name
                st.session_state.scanned_input_path = input_path
                st.session_state.scanned_output_path = output_path

        if st.session_state.get("scanned_file") == uploaded.name:
            detections = st.session_state.detections

            if not detections:
                st.info("No PII patterns were detected.")
            else:
                st.subheader(f"Review: {len(detections)} match(es) found")
                st.caption("Uncheck anything that looks like a false positive before redacting.")

                confirmed_ids = []
                for d in detections:
                    checked = st.checkbox(
                        f"Page {d['page']}: {d['label']} — \"{d['text']}\"",
                        value=True,
                        key=f"det_{d['id']}",
                    )
                    if checked:
                        confirmed_ids.append(d["id"])
                    with st.expander("Why is this sensitive?", expanded=False):
                        st.caption(get_citation(d["label"]))

                st.divider()

                if st.button(f"Apply redaction to {len(confirmed_ids)} selected item(s)", disabled=len(confirmed_ids) == 0):
                    allowed, limit_msg = check_rate_limit(st.session_state.redaction_count, 1)
                    if not allowed:
                        st.error(limit_msg)
                    else:
                        confirmed = [d for d in detections if d["id"] in confirmed_ids]
                        with st.spinner("Redacting selected items..."):
                            apply_redactions(input_path, output_path, confirmed)
                            log_session(uploaded.name, LLM_BACKEND, detections, set(confirmed_ids))
                        st.session_state.redaction_count += 1

                        st.success(f"Redacted {len(confirmed)} item(s). Nothing left this machine.")

                        with open(output_path, "rb") as f:
                            st.download_button("Download redacted file", f, file_name=f"redacted_{uploaded.name}")

                        with st.spinner("Building a safe search index over the redacted content..."):
                            if os.path.isdir(INDEX_DIR):
                                shutil.rmtree(INDEX_DIR)
                            build_chat_index(output_path, INDEX_DIR)
                        st.info("You can now ask questions about this document in the Chat tab.")

    st.divider()
    st.caption(
        "⚠️ Known limitation: detection is regex/pattern-based. It does not detect "
        "names, addresses, or other free-text PII — this is a targeted tool, not a "
        "general PII scanner. Long numeric identifiers can occasionally be misflagged "
        "as account numbers (e.g. order references) — the review step above exists "
        "specifically to catch cases like this before anything is redacted."
    )

with tab_batch:
    st.caption(f"Session usage: {st.session_state.redaction_count}/{DEFAULT_LIMIT} redactions")
    st.write(
        "Redact several documents at once. **Tradeoff:** batch mode redacts every "
        "detection automatically with no per-item review step — the single-file "
        "Redact tab's checklist doesn't scale to reviewing many files in one sitting. "
        "Use single-file mode when you need to catch false positives; use batch mode "
        "for throughput on documents you trust the detector's judgment on."
    )

    batch_files = st.file_uploader(
        "Upload multiple documents", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True
    )

    if batch_files and st.button(f"Redact all {len(batch_files)} file(s)"):
        allowed, limit_msg = check_rate_limit(st.session_state.redaction_count, len(batch_files))
        if not allowed:
            st.error(limit_msg)
        else:
            batch_input_paths = []
            for f in batch_files:
                path = os.path.join(UPLOAD_DIR, f.name)
                with open(path, "wb") as out:
                    out.write(f.getbuffer())
                batch_input_paths.append(path)

            with st.spinner(f"Redacting {len(batch_input_paths)} file(s)..."):
                results = process_batch(batch_input_paths, BATCH_OUTPUT_DIR)
                zip_bytes = zip_results(results)
            st.session_state.redaction_count += len(batch_files)

            st.success(f"Redacted {len(results)} file(s).")
            summary_df = pd.DataFrame([
                {"filename": r["filename"], "items_redacted": len(r["audit_log"])} for r in results
            ])
            st.dataframe(summary_df, use_container_width=True)

            st.download_button(
                "Download all redacted files (.zip)", zip_bytes,
                file_name="maskfin_batch_redacted.zip", mime="application/zip",
            )

with tab_chat:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if not os.path.isdir(INDEX_DIR):
        st.warning("Redact a document in the Redact tab first — chat only runs over redacted content.")
    else:
        for turn in st.session_state.chat_messages:
            with st.chat_message(turn["role"]):
                st.write(turn["content"])

        question = st.chat_input("Ask about the redacted document...")
        if question:
            st.session_state.chat_messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    chain = build_chain(INDEX_DIR)
                    response = ask(chain, question)
                st.write(response["answer"])
                if response["sources"]:
                    src_str = ", ".join(f"{f} (p.{p})" for f, p in response["sources"])
                    st.caption(f"Sources: {src_str} · {response['latency_seconds']}s")
            st.session_state.chat_messages.append({"role": "assistant", "content": response["answer"]})

with tab_history:
    st.write(
        "Every redaction session, logged locally. **Note:** this log stores labels "
        "and counts only — never the actual PAN/Aadhaar/card numbers found, since a "
        "growing database of real PII values would itself become a liability."
    )

    sessions = get_all_sessions()
    if not sessions:
        st.info("No sessions logged yet. Redact a document to see it appear here.")
    else:
        sessions_df = pd.DataFrame(sessions)[
            ["filename", "timestamp", "backend", "total_detected", "total_redacted"]
        ]
        st.dataframe(sessions_df, use_container_width=True)

        selected_id = st.selectbox(
            "View item breakdown for session", options=[s["id"] for s in sessions],
            format_func=lambda sid: next(s["filename"] for s in sessions if s["id"] == sid),
        )
        if selected_id:
            items = get_session_items(selected_id)
            if not items:
                st.info("No PII was detected in this document.")
            else:
                items_df = pd.DataFrame(items)[["page", "label", "redacted"]]
                st.dataframe(items_df, use_container_width=True)
