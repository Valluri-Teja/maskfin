"""
batch.py
Batch redaction: process multiple documents in one pass.

Design tradeoff, stated explicitly: batch mode redacts everything the
detector finds in each file, with no per-item manual review step. The
single-file "Redact" tab's review-before-confirm flow doesn't scale to
reviewing dozens of checkboxes across many files in one sitting, so
batch mode trades that safety net for throughput. This is a deliberate
choice, not an oversight - documented here and in the UI so it's an
informed one.
"""

import os
import zipfile
import io

from redact import redact_file
from history import log_session
from qa_chain import LLM_BACKEND


def process_batch(file_paths: list, output_dir: str) -> list:
    """
    Redact every file in file_paths (auto-confirming all detections,
    no manual review). Returns a list of per-file results:
    [{"filename": ..., "output_path": ..., "audit_log": [...]}, ...]
    Also logs each file's session to the persistent history database.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for input_path in file_paths:
        filename = os.path.basename(input_path)
        output_path = os.path.join(output_dir, f"redacted_{filename}")

        audit_log = redact_file(input_path, output_path)

        fake_detections = [
            {"id": i, "page": entry["page"], "label": entry["label"]}
            for i, entry in enumerate(audit_log)
        ]
        confirmed_ids = set(range(len(audit_log)))
        log_session(filename, LLM_BACKEND, fake_detections, confirmed_ids)

        results.append({
            "filename": filename,
            "output_path": output_path,
            "audit_log": audit_log,
        })

    return results


def zip_results(results: list) -> bytes:
    """Package every redacted output file into a single zip, returned as bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            zf.write(r["output_path"], arcname=os.path.basename(r["output_path"]))
    buf.seek(0)
    return buf.read()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python batch.py <output_dir> <file1> [file2 ...]")
        sys.exit(1)

    output_dir, *files = sys.argv[1:]
    results = process_batch(files, output_dir)
    for r in results:
        print(f"{r['filename']}: {len(r['audit_log'])} item(s) redacted -> {r['output_path']}")
