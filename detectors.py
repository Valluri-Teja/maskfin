"""
detectors.py
OCR + regex-based detection of Indian financial PII in document images:
PAN, Aadhaar, bank account numbers, IFSC codes.

Patterns are checked in priority order (most specific first) with
overlap suppression, so e.g. a 12-digit Aadhaar number without spaces
doesn't also get logged as a generic account number.
"""

import re
import pytesseract
from PIL import Image

PATTERNS = [
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),
    ("Aadhaar", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("Account Number", re.compile(r"\b\d{9,18}\b")),
]


def _extract_words_with_offsets(image: Image.Image):
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words = []
    char_pos = 0
    text_parts = []
    for i in range(len(data["text"])):
        text = data["text"][i]
        if not text.strip():
            continue
        start = char_pos
        end = char_pos + len(text)
        words.append({
            "text": text, "start": start, "end": end,
            "left": data["left"][i], "top": data["top"][i],
            "width": data["width"][i], "height": data["height"][i],
        })
        text_parts.append(text)
        char_pos = end + 1

    full_text = " ".join(text_parts)
    return full_text, words


def detect_pii(image: Image.Image) -> list:
    full_text, words = _extract_words_with_offsets(image)
    detections = []
    claimed_spans = []

    for label, pattern in PATTERNS:
        for m in pattern.finditer(full_text):
            m_start, m_end = m.start(), m.end()
            if any(m_start < c_end and m_end > c_start for c_start, c_end in claimed_spans):
                continue

            covering = [w for w in words if w["start"] < m_end and w["end"] > m_start]
            if not covering:
                continue

            x0 = min(w["left"] for w in covering)
            y0 = min(w["top"] for w in covering)
            x1 = max(w["left"] + w["width"] for w in covering)
            y1 = max(w["top"] + w["height"] for w in covering)

            detections.append({"label": label, "text": m.group(), "box": (x0, y0, x1, y1)})
            claimed_spans.append((m_start, m_end))

    return detections
