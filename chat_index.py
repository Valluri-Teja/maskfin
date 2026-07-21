"""
chat_index.py
Builds a RAG index over a document's text AFTER redaction, not before.
The raw PII never gets embedded or indexed - it's destroyed before
this function ever runs.
"""

import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _ocr_redacted_file(redacted_path: str) -> list:
    ext = os.path.splitext(redacted_path)[1].lower()
    if ext == ".pdf":
        pages = convert_from_path(redacted_path, dpi=200)
    else:
        pages = [Image.open(redacted_path)]

    documents = []
    for page_num, page_img in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page_img)
        documents.append(Document(
            page_content=text,
            metadata={"source": os.path.basename(redacted_path), "page": page_num},
        ))
    return documents


def build_chat_index(redacted_path: str, index_dir: str) -> FAISS:
    documents = _ocr_redacted_file(redacted_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(index_dir)
    return vectorstore
