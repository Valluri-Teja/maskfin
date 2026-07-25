"""
detect.py
Phase 1 of the review-before-redact flow: scan a document and return
every detected PII match, without touching the file. Redaction is a
separate, explicit step (see redact.py's apply_redactions), so the
user can review and deselect false positives before anything is
committed - this is what turns "auto-redact everything" into
"confirm before you commit."
"""

import os
from PIL import Image
from pdf2image import convert_from_path

from detectors import detect_pii

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}


def load_pages(input_path: str) -> list:
    """Load a PDF or image file into a list of PIL Image pages."""
    ext = os.path.splitext(input_path)[1].lower()
    if ext in PDF_EXTENSIONS:
        return convert_from_path(input_path, dpi=200)
    elif ext in IMAGE_EXTENSIONS:
        return [Image.open(input_path)]
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PDF, JPG, or PNG.")


def scan_document(input_path: str) -> list:
    """
    Scan every page of input_path and return every detection found,
    without redacting anything. Each detection gets a stable id so the
    UI can track which ones the user confirmed or rejected.

    Returns: [{"id": 0, "page": 1, "label": "PAN", "text": "ABCDE1234F",
               "box": (x0,y0,x1,y1)}, ...]
    """
    pages = load_pages(input_path)
    all_detections = []
    detection_id = 0
    for page_num, page_img in enumerate(pages, start=1):
        for d in detect_pii(page_img):
            all_detections.append({
                "id": detection_id,
                "page": page_num,
                "label": d["label"],
                "text": d["text"],
                "box": d["box"],
            })
            detection_id += 1
    return all_detections
