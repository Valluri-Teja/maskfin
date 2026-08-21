"""
tests/generate_test_set.py
Builds a small labeled test set of synthetic documents with known
ground-truth PII, used by eval_accuracy.py to measure detector
precision/recall. Includes true positives across all 9 PII types, a
true negative, a Luhn-invalid decoy, and a genuine multi-page document.
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


def _make_multipage_pdf(filename):
    """A genuine 2-page PDF, to test that page numbers are tracked
    correctly across pages, not just within a single page."""
    path = os.path.join(OUT_DIR, filename)
    c = canvas.Canvas(path)
    c.drawString(100, 750, "Page 1 of statement")
    c.drawString(100, 730, "PAN: ABCDE1234F")
    c.showPage()
    c.drawString(100, 750, "Page 2 of statement")
    c.drawString(100, 730, "IFSC: HDFC0001234")
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
    {
        "filename": "doc6_expanded_pii_types.pdf",
        "lines": [
            "KYC Verification Form",
            "GSTIN: 27AAAAA0000A1Z5",
            "Passport: A1234567",
            "Card Number: 4111 1111 1111 1111",
            "Phone: 9876543210",
            "Email: test.user@example.com",
        ],
        "ground_truth": [
            {"label": "GSTIN", "text": "27AAAAA0000A1Z5"},
            {"label": "Passport", "text": "A1234567"},
            {"label": "Card Number", "text": "4111 1111 1111 1111"},
            {"label": "Phone Number", "text": "9876543210"},
            {"label": "Email", "text": "test.user@example.com"},
        ],
    },
    {
        "filename": "doc7_invalid_luhn_card_decoy.pdf",
        "lines": [
            "Internal Reference Document",
            "Tracking Code: 1234 5678 9012 3456",
            "This 16-digit code fails the Luhn checksum and should NOT",
            "be flagged as a card number.",
        ],
        "ground_truth": [
            {"label": "Account Number", "text": "1234567890123456"},
        ],
        "note": "Tests that Luhn validation correctly rejects an invalid card-shaped number",
    },
    {
        "filename": "doc8_all_clean_business_letter.pdf",
        "lines": [
            "Dear Sir/Madam,",
            "Thank you for your continued business with us this quarter.",
            "We look forward to serving you again soon.",
            "Regards, Customer Relations Team",
        ],
        "ground_truth": [],
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

    multipage_path = _make_multipage_pdf("doc9_multipage.pdf")
    manifest.append({
        "path": multipage_path,
        "ground_truth": [
            {"label": "PAN", "text": "ABCDE1234F"},
            {"label": "IFSC", "text": "HDFC0001234"},
        ],
        "note": "Multi-page document - page-number correctness is checked separately in test_redact.py",
    })

    return manifest


if __name__ == "__main__":
    manifest = build_all()
    print(f"Generated {len(manifest)} test documents in {OUT_DIR}/")
    for m in manifest:
        print(f"  {os.path.basename(m['path'])}: {len(m['ground_truth'])} expected detection(s)")
