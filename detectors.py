"""
detectors.py
OCR + regex-based detection of Indian financial and personal PII in
document images: PAN, Aadhaar, bank account numbers, IFSC, GSTIN,
passport numbers, credit/debit cards (Luhn-validated), phone numbers,
and email addresses.

Patterns are checked in priority order (most specific first) with
overlap suppression, so e.g. a 12-digit Aadhaar number without spaces
doesn't also get logged as a generic account number, and a 16-digit
card number claims its span before the generic account-number pattern
can grab part of it.

Credit/debit card candidates are validated with the Luhn checksum
algorithm before being accepted - this is a real accuracy improvement
over pure regex, since Luhn rejects the vast majority of random
16-digit strings that aren't actually valid card numbers, while a
plain \d{16} pattern would flag all of them.
"""

import re
import pytesseract
from PIL import Image


def _luhn_check(number: str) -> bool:
    """Standard Luhn checksum, used to validate card-number candidates
    before accepting them - reduces false positives versus a bare
    digit-count regex."""
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 12:
        return False
    digits.reverse()
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# (label, compiled regex, optional validator(match_text) -> bool)
# Order matters: most specific / highest-confidence patterns first,
# so overlap suppression lets them claim their span before broader
# patterns (like Account Number) can partially match the same text.
#
# Card Number MUST come before Aadhaar: a 16-digit card number grouped
# in 4s ("4111 1111 1111 1111") starts with the exact same shape as a
# 12-digit Aadhaar number ("4111 1111 1111"). If Aadhaar is checked
# first, it greedily claims the first 12 digits, leaving the card
# pattern unable to match the (now-overlapping) remaining span - the
# last 4 digits of the card would go completely undetected. Checking
# the longer, more specific pattern first avoids this.
PATTERNS = [
    ("Email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), None),
    ("GSTIN", re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"), None),
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), None),
    ("Passport", re.compile(r"\b[A-Z]\d{7}\b"), None),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"), None),
    ("Card Number", re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), _luhn_check),
    ("Aadhaar", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), None),
    ("Phone Number", re.compile(r"(?:\+91[-\s]?)?\b[6-9]\d{9}\b"), None),
    ("Account Number", re.compile(r"\b\d{9,18}\b"), None),
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
    """
    Returns: [{"label": "PAN", "text": "ABCDE1234F", "box": (x0, y0, x1, y1)}, ...]
    """
    full_text, words = _extract_words_with_offsets(image)
    detections = []
    claimed_spans = []

    for label, pattern, validator in PATTERNS:
        for m in pattern.finditer(full_text):
            m_start, m_end = m.start(), m.end()
            if any(m_start < c_end and m_end > c_start for c_start, c_end in claimed_spans):
                continue
            if validator is not None and not validator(m.group()):
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
