## Live Demo

**https://maskfin.onrender.com**

Note: runs on Render's free tier, which spins down after 15 minutes of inactivity - first load after idle time may take 30-60 seconds to wake up.

# MaskFin

Offline PII redaction for Indian financial documents. PAN, Aadhaar,
bank account numbers, and IFSC codes are detected and destroyed
entirely on your machine Ã¢â‚¬â€ no cloud API calls, no external upload of
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
documents already issued by an authority Ã¢â‚¬â€ the point is proving
they're authentic and unmodified. MaskFin solves a different problem:
you already have a document (e.g. a bank statement) and need to share
*part* of it with a third party without exposing PAN, Aadhaar, or
account numbers. DigiLocker has no redaction concept and is a cloud
service by design; MaskFin runs entirely offline.

## Architecture
### Why regex, not a trained model, for detection
PAN, Aadhaar, account numbers, and IFSC codes all have rigid,
well-defined formats (a PAN is always 5 letters + 4 digits + 1 letter,
no exceptions). Regex is the right tool for fixed-format identifiers Ã¢â‚¬â€
a heavyweight ML model would be over-engineering here. The real ML in
this project is OCR (Tesseract, a trained model for reading text out
of scanned images) and the LLM used for chat.

### Why redaction happens before indexing, not after
This is the core privacy decision: the RAG chat index is built only
from the OCR output of the *already-redacted* document. The chat LLM
never has access to the real PAN, Aadhaar, or account number at any
point in the pipeline Ã¢â‚¬â€ it's structurally excluded, not filtered at
display time.

## Setup

Requires Tesseract OCR and poppler installed locally (not pip
packages):
- Windows: [Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki),
  [poppler](https://github.com/oschwartz10612/poppler-windows/releases) Ã¢â‚¬â€
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
  free-text PII Ã¢â‚¬â€ a general-purpose PII scanner would need a trained
  NER model for that, which is intentionally out of scope here.
- `compliance_corpus.txt` is a paraphrased summary of general DPDP Act
  principles, written for this project Ã¢â‚¬â€ not verbatim legal text, not
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

## Run with Docker (recommended - avoids manual Tesseract/poppler setup)

```bash
docker build -t maskfin .
docker run -p 8501:8501 -e GROQ_API_KEY="your_key_here" maskfin
```

This bakes Tesseract OCR and poppler into the image, so there's no need
to install or manually add either to PATH on the host machine - the
exact setup friction that motivated adding this in the first place.

## Screenshots

**Review before redact Ã¢â‚¬â€ every match shown, nothing redacted until confirmed:**
![Redact review screen](screenshots/redact-review.png)

**Persistent audit history Ã¢â‚¬â€ labels and counts only, never raw PII:**
![History tab](screenshots/history-tab.png)

**Batch processing Ã¢â‚¬â€ multiple files, one zip download:**
![Batch tab](screenshots/batch-tab.png)

## Additional known limitations (production-readiness notes)

- **SQLite concurrency**: history.py uses a single SQLite file. Under
  concurrent writes (e.g. simultaneous batch uploads from different
  users on the live deployment), SQLite's file-level locking can cause
  write contention. Fine for a single-instance demo; a real production
  deployment would need a proper client-server database (Postgres) or
  a queue in front of writes.
- **Rate limiting is in-memory, per-session, single-instance only**
  (rate_limit.py). It resets on page refresh and doesn't coordinate
  across multiple server instances. The correct production upgrade
  would be a shared store (Redis) for rate limit state, not built here
  since this runs as a single free-tier instance.
## Additional known limitations (production-readiness notes)

- **SQLite concurrency**: history.py uses a single SQLite file. Under
  concurrent writes (e.g. simultaneous batch uploads from different
  users on the live deployment), SQLite's file-level locking can cause
  write contention. Fine for a single-instance demo; a real production
  deployment would need a proper client-server database (Postgres) or
  a queue in front of writes.
- **Rate limiting is in-memory, per-session, single-instance only**
  (rate_limit.py). It resets on page refresh and doesn't coordinate
  across multiple server instances. The correct production upgrade
  would be a shared store (Redis) for rate limit state, not built here
  since this runs as a single free-tier instance.