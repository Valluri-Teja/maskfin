"""
tests/test_redact.py
Edge-case tests for the redaction pipeline: unsupported file types,
documents with zero detected PII, and empty confirmed-selection lists.

Run with: pytest tests/test_redact.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from reportlab.pdfgen import canvas

from redact import redact_file, apply_redactions
from detect import scan_document


@pytest.fixture
def clean_pdf(tmp_path):
    path = str(tmp_path / "clean.pdf")
    c = canvas.Canvas(path)
    c.drawString(100, 750, "This document contains no sensitive information.")
    c.save()
    return path


@pytest.fixture
def pan_pdf(tmp_path):
    path = str(tmp_path / "with_pan.pdf")
    c = canvas.Canvas(path)
    c.drawString(100, 750, "PAN: ABCDE1234F")
    c.save()
    return path


def test_redact_file_rejects_unsupported_extension(tmp_path):
    bad_path = str(tmp_path / "document.txt")
    with open(bad_path, "w") as f:
        f.write("not a real document")
    with pytest.raises(ValueError, match="Unsupported file type"):
        redact_file(bad_path, str(tmp_path / "out.txt"))


def test_redact_file_on_clean_document_returns_empty_log(clean_pdf, tmp_path):
    output_path = str(tmp_path / "clean_out.pdf")
    audit_log = redact_file(clean_pdf, output_path)
    assert audit_log == []
    assert os.path.exists(output_path)


def test_scan_document_on_clean_document_returns_no_detections(clean_pdf):
    detections = scan_document(clean_pdf)
    assert detections == []


def test_apply_redactions_with_empty_confirmed_list_leaves_pii_untouched(pan_pdf, tmp_path):
    output_path = str(tmp_path / "unredacted_out.pdf")
    apply_redactions(pan_pdf, output_path, confirmed_detections=[])

    assert os.path.exists(output_path)

    remaining = scan_document(output_path)
    labels = [d["label"] for d in remaining]
    assert "PAN" in labels


def test_apply_redactions_actually_removes_confirmed_items(pan_pdf, tmp_path):
    output_path = str(tmp_path / "redacted_out.pdf")
    detections = scan_document(pan_pdf)
    assert len(detections) == 1

    apply_redactions(pan_pdf, output_path, confirmed_detections=detections)

    remaining = scan_document(output_path)
    assert remaining == []
