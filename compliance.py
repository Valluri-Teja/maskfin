"""
compliance.py
Tiny local RAG index over compliance_corpus.txt, attaching a "why is
this sensitive" citation to each redacted field. This corpus is a
paraphrased summary of general principles from India's DPDP Act and
related frameworks, written for this project - it is NOT verbatim
legal text and should not be treated as legal advice.

chunk_size=600 is deliberately chosen (not the more common 800): with
10 short sections of varying length, a chunk_size of 800 was found to
merge some adjacent short sections together (e.g. Passport + Card,
Phone + Email), which degraded citation precision - the retrieved
chunk for "Card Number" would start with unrelated Passport text.
600 sits between the longest single section (555 chars) and the
smallest pair of adjacent sections combined (694 chars), guaranteeing
each section splits into its own chunk.
"""

import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "compliance_corpus.txt")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_vectorstore = None


def _get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        docs = TextLoader(CORPUS_PATH).load()
        splitter = CharacterTextSplitter(separator="\n\n", chunk_size=600, chunk_overlap=0)
        chunks = splitter.split_documents(docs)
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        _vectorstore = FAISS.from_documents(chunks, embeddings)
    return _vectorstore


def get_citation(label: str) -> str:
    vectorstore = _get_vectorstore()
    results = vectorstore.similarity_search(label, k=1)
    if not results:
        return "No specific compliance note available for this field."
    return results[0].page_content.strip()


if __name__ == "__main__":
    for label in ["PAN", "Aadhaar", "Account Number", "IFSC", "GSTIN",
                  "Passport", "Card Number", "Phone Number", "Email"]:
        print(f"=== {label} ===")
        print(get_citation(label))
        print()
