"""
qa_chain.py
Conversational RAG chain over an already-redacted document's index.
"""

import os
import time
from langchain_community.llms import CTransformers
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_PATH = os.environ.get(
    "MISTRAL_GGUF_PATH",
    r"D:\intern\langchain_project\models\mistral-7b-instruct-v0.2.Q5_K_M.gguf",
)
LLM_BACKEND = os.environ.get("LLM_BACKEND", "local")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

DOCUMENT_PROMPT = PromptTemplate(
    input_variables=["page_content", "source", "page"],
    template="[{source}, p.{page}]\n{page_content}",
)

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "You are answering questions about a document that has already had "
        "all PAN, Aadhaar, account number, and IFSC data redacted before "
        "you ever saw it. Use ONLY the context below. Every claim must end "
        "with a citation [filename, p.N]. If asked for redacted information, "
        "explain that it was removed for privacy and is not available to you. "
        "If the answer isn't in the context, say you don't know.\n\n"
        "Context:\n{context}\n\nQuestion: {question}\n"
        "Answer (2-4 sentences, with inline citations):"
    ),
)


def get_llm():
    if LLM_BACKEND == "groq":
        if not GROQ_API_KEY:
            raise ValueError("LLM_BACKEND=groq requires GROQ_API_KEY to be set.")
        return ChatOpenAI(
            model=GROQ_MODEL, openai_api_key=GROQ_API_KEY,
            openai_api_base="https://api.groq.com/openai/v1",
            temperature=0.2, max_tokens=256,
        )
    return CTransformers(
        model=MODEL_PATH, model_type="mistral",
        config={"max_new_tokens": 256, "temperature": 0.2, "context_length": 4096},
    )


def build_chain(index_dir: str, k: int = 4) -> ConversationalRetrievalChain:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    llm = get_llm()

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=retriever, memory=memory,
        combine_docs_chain_kwargs={"prompt": QA_PROMPT, "document_prompt": DOCUMENT_PROMPT},
        return_source_documents=True,
    )
    return chain


def ask(chain: ConversationalRetrievalChain, question: str) -> dict:
    start = time.monotonic()
    result = chain.invoke({"question": question})
    elapsed = round(time.monotonic() - start, 2)
    sources = sorted({
        (doc.metadata.get("source", "unknown"), doc.metadata.get("page", "?"))
        for doc in result["source_documents"]
    })
    return {"answer": result["answer"], "sources": sources, "latency_seconds": elapsed}
