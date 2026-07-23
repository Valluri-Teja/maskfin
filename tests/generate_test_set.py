"""
tests/generate_test_set.py
Builds a small labeled test set of synthetic documents with known
ground-truth PII, used by eval_accuracy.py to measure detector
precision/recall. Includes true positives, a true negative (no PII),
and a known false positive case (documented, not hidden) to give an
honest accuracy picture rather than a cherry-picked one.
"""

import os
from reportlab.pdfgen import canvas

OUT_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _make_pdf(filename, lines):
    path = os.path.join(OUT_DIR, filename)
    c = canvas.Canvas(path)
    y = 750
    for line in lines:
        c.drawString(100, y, line)
        y -= 20
    c.save()
    return path


TEST_CASES = [
    {
        "filename": "doc1_standard.pdf",
        "lines": [
            "Bank Statement - Account Holder: Rajesh Kumar",
            "PAN: ABCDE1234F",
            "Aadhaar: 1234 5678 9012",
            "Account Number: 50100234567890",
            "IFSC: HDFC0001234",
            "Total Balance: Rs 45,230.50",
        ],
        "ground_truth": [
            {"label": "PAN", "text": "ABCDE1234F"},
            {"label": "Aadhaar", "text": "1234 5678 9012"},
            {"label": "Account Number", "text": "50100234567890"},
            {"label": "IFSC", "text": "HDFC0001234"},
        ],
    },
    {
        "filename": "doc2_aadhaar_no_spaces.pdf",
        "lines": [
            "Identity Verification Document",
            "Aadhaar Number: 987654321098",
            "PAN Card: XYZAB5678C",
        ],
        "ground_truth": [
            {"label": "Aadhaar", "text": "987654321098"},
            {"label": "PAN", "text": "XYZAB5678C"},
        ],
    },
    {
        "filename": "doc3_no_pii.pdf",
        "lines": [
            "Weekly Weather Summary",
            "This week has been mostly sunny with occasional clouds.",
            "Temperatures ranged from 24 to 31 degrees Celsius.",
            "No rainfall was recorded during the observation period.",
        ],
        "ground_truth": [],
    },
    {
        "filename": "doc4_decoy_reference_number.pdf",
        "lines": [
            "Order Confirmation",
            "Order Reference: 100234567890123",
            "Thank you for your purchase.",
        ],
        "ground_truth": [
            {"label": "Account Number", "text": "100234567890123"},
        ],
        "note": "Expected false positive - order reference misclassified as account number",
    },
    {
        "filename": "doc5_multiple_same_type.pdf",
        "lines": [
            "Joint Account Statement",
            "Primary Holder PAN: AAAAA1111A",
            "Secondary Holder PAN: BBBBB2222B",
            "IFSC: SBIN0009876",
        ],
        "ground_truth": [
            {"label": "PAN", "text": "AAAAA1111A"},
            {"label": "PAN", "text": "BBBBB2222B"},
            {"label": "IFSC", "text": "SBIN0009876"},
        ],
    },
]


def build_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = []
    for case in TEST_CASES:
        path = _make_pdf(case["filename"], case["lines"])
        manifest.append({
            "path": path,
            "ground_truth": case["ground_truth"],
            "note": case.get("note", ""),
        })
    return manifest


if __name__ == "__main__":
    manifest = build_all()
    print(f"Generated {len(manifest)} test documents in {OUT_DIR}/")
    for m in manifest:
        print(f"  {os.path.basename(m['path'])}: {len(m['ground_truth'])} expected detection(s)")
