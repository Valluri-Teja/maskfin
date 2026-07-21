"""
app.py
MaskFin: offline PII redaction + safe RAG chat over financial documents.
Run with: streamlit run app.py
"""

import os
import shutil
import streamlit as st

from redact import redact_file
from compliance import get_citation
from chat_index import build_chat_index
from qa_chain import build_chain, ask, LLM_BACKEND

st.set_page_config(page_title="MaskFin", layout="wide")
st.title("🛡️ MaskFin")
st.caption(
    f"Offline PII redaction for financial documents. PAN, Aadhaar, account "
    f"numbers, and IFSC codes are detected and destroyed locally — the "
    f"unredacted file never leaves your machine. LLM backend: **{LLM_BACKEND}**"
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "redacted"
INDEX_DIR = "chat_index"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

tab_redact, tab_chat = st.tabs(["🖍️ Redact", "💬 Chat (redacted doc only)"])

with tab_redact:
    uploaded = st.file_uploader("Upload a bank statement or ID document", type=["pdf", "jpg", "jpeg", "png"])

    if uploaded:
        input_path = os.path.join(UPLOAD_DIR, uploaded.name)
        with open(input_path, "wb") as f:
            f.write(uploaded.getbuffer())

        output_path = os.path.join(OUTPUT_DIR, f"redacted_{uploaded.name}")

        if st.button("Redact this document"):
            with st.spinner("Running OCR and detecting PII locally..."):
                audit_log = redact_file(input_path, output_path)

            st.success(f"Redacted {len(audit_log)} item(s). Nothing left this machine.")

            if audit_log:
                st.subheader("Audit log")
                for entry in audit_log:
                    with st.expander(f"Page {entry['page']}: {entry['label']} redacted"):
                        st.caption(get_citation(entry["label"]))
            else:
                st.info("No PAN, Aadhaar, account number, or IFSC patterns were detected.")

            with open(output_path, "rb") as f:
                st.download_button("Download redacted file", f, file_name=f"redacted_{uploaded.name}")

            with st.spinner("Building a safe search index over the redacted content..."):
                if os.path.isdir(INDEX_DIR):
                    shutil.rmtree(INDEX_DIR)
                build_chat_index(output_path, INDEX_DIR)
            st.info("You can now ask questions about this document in the Chat tab.")

    st.divider()
    st.caption(
        "⚠️ Known limitation: detection is regex/pattern-based for PAN, Aadhaar, "
        "account numbers, and IFSC codes. It does not detect names, addresses, "
        "or other free-text PII — this is a targeted tool, not a general PII scanner."
    )

with tab_chat:
    if "history" not in st.session_state:
        st.session_state.history = []

    if not os.path.isdir(INDEX_DIR):
        st.warning("Redact a document in the Redact tab first — chat only runs over redacted content.")
    else:
        for turn in st.session_state.history:
            with st.chat_message(turn["role"]):
                st.write(turn["content"])

        question = st.chat_input("Ask about the redacted document...")
        if question:
            st.session_state.history.append({"role": "user", "content": question})
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
            st.session_state.history.append({"role": "assistant", "content": response["answer"]})
