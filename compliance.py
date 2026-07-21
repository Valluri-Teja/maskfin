"""
compliance.py
Tiny local RAG index over compliance_corpus.txt, attaching a "why is
this sensitive" citation to each redacted field. This corpus is a
paraphrased summary of general principles from India's DPDP Act and
related frameworks, written for this project - it is NOT verbatim
legal text and should not be treated as legal advice.
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
        splitter = CharacterTextSplitter(separator="\n\n", chunk_size=800, chunk_overlap=0)
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
    for label in ["PAN", "Aadhaar", "Account Number", "IFSC"]:
        print(f"=== {label} ===")
        print(get_citation(label))
        print()
