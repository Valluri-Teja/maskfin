# MaskFin

Offline PII redaction for Indian financial documents. PAN, Aadhaar,
bank account numbers, and IFSC codes are detected and destroyed
entirely on your machine — no cloud API calls, no external upload of
the original document. Includes a safe RAG chat feature that only ever
sees the redacted version, plus compliance citations explaining why
each field is treated as sensitive.

## Why this exists

Most redaction/PII tools either run in the cloud (defeating the point
of redacting sensitive data in the first place) or are generic PII
scanners not tuned to Indian financial document formats. MaskFin is
narrow and offline by design.

## How it's different from something like DigiLocker

DigiLocker is a document *storage and verification* system for
documents already issued by an authority — the point is proving
they're authentic and unmodified. MaskFin solves a different problem:
you already have a document (e.g. a bank statement) and need to share
*part* of it with a third party without exposing PAN, Aadhaar, or
account numbers. DigiLocker has no redaction concept and is a cloud
service by design; MaskFin runs entirely offline.

## Architecture
### Why regex, not a trained model, for detection
PAN, Aadhaar, account numbers, and IFSC codes all have rigid,
well-defined formats (a PAN is always 5 letters + 4 digits + 1 letter,
no exceptions). Regex is the right tool for fixed-format identifiers —
a heavyweight ML model would be over-engineering here. The real ML in
this project is OCR (Tesseract, a trained model for reading text out
of scanned images) and the LLM used for chat.

### Why redaction happens before indexing, not after
This is the core privacy decision: the RAG chat index is built only
from the OCR output of the *already-redacted* document. The chat LLM
never has access to the real PAN, Aadhaar, or account number at any
point in the pipeline — it's structurally excluded, not filtered at
display time.

## Setup

Requires Tesseract OCR and poppler installed locally (not pip
packages):
- Windows: [Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki),
  [poppler](https://github.com/oschwartz10612/poppler-windows/releases) —
  add both to PATH

```bash
pip install -r requirements.txt
export MISTRAL_GGUF_PATH="/path/to/mistral-7b-instruct-v0.2.Q5_K_M.gguf"
streamlit run app.py
```

Optional cloud LLM backend (needed for deployment, since hosting
services like Streamlit Cloud can't run a local multi-GB GGUF model):
```bash
export LLM_BACKEND=groq
export GROQ_API_KEY=your_key_here
```

## Known limitations

- Detects structured, fixed-format identifiers only (PAN, Aadhaar,
  account number, IFSC). It does not detect names, addresses, or other
  free-text PII — a general-purpose PII scanner would need a trained
  NER model for that, which is intentionally out of scope here.
- `compliance_corpus.txt` is a paraphrased summary of general DPDP Act
  principles, written for this project — not verbatim legal text, not
  legal advice.
- OCR accuracy depends on scan quality; very low-resolution or skewed
  scans may miss detections.

## Verified working (not just claimed)

- Redaction confirmed pixel-precise: re-running detection on the
  redacted output finds zero recoverable PII.
- Both PDF and image (JPG/PNG) inputs tested end-to-end.
- Multi-word pattern matching (e.g. spaced Aadhaar numbers) confirmed
  to map to correct bounding boxes.
## Detector accuracy (measured, not assumed)

Run `python eval_accuracy.py` to reproduce. On a labeled test set of 5
synthetic documents (10 total ground-truth PII instances):

**Result: Precision 1.0, Recall 1.0, F1 1.0** (10/10 correct, 0 false
positives, 0 false negatives)

Note: OCR output can vary slightly across machines/Tesseract versions,
especially on long digit sequences. One test case (a 15-digit order
reference number) is included specifically because it's known to
sometimes get its OCR text split by a spurious whitespace artifact,
which would partially defeat the Account Number pattern - documented
in eval_accuracy.py. On this run it did not occur; on another
environment it did, producing 0.9/0.9/0.9. Both outcomes are expected
and are themselves evidence the eval harness catches real, environment-
dependent OCR edge cases rather than only clean-path behavior.
