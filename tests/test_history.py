"""
tests/test_history.py
Tests for the persistent audit trail - most importantly, an automated
version of the privacy guarantee: raw PII values must never be
written to the history database, only labels and counts.

Run with: pytest tests/test_history.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import history


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_history.db")


def test_log_session_stores_correct_counts(temp_db):
    detections = [
        {"id": 0, "page": 1, "label": "PAN", "text": "ABCDE1234F"},
        {"id": 1, "page": 1, "label": "IFSC", "text": "HDFC0001234"},
        {"id": 2, "page": 2, "label": "Aadhaar", "text": "1234 5678 9012"},
    ]
    sid = history.log_session("test.pdf", "groq", detections, confirmed_ids={0, 2}, db_path=temp_db)

    sessions = history.get_all_sessions(db_path=temp_db)
    session = next(s for s in sessions if s["id"] == sid)
    assert session["total_detected"] == 3
    assert session["total_redacted"] == 2


def test_log_session_never_stores_raw_pii_values(temp_db):
    detections = [
        {"id": 0, "page": 1, "label": "PAN", "text": "ABCDE1234F"},
        {"id": 1, "page": 1, "label": "Aadhaar", "text": "1234 5678 9012"},
    ]
    history.log_session("test.pdf", "groq", detections, confirmed_ids={0, 1}, db_path=temp_db)

    with open(temp_db, "rb") as f:
        raw_bytes = f.read()

    assert b"ABCDE1234F" not in raw_bytes
    assert b"1234 5678 9012" not in raw_bytes
    assert b"PAN" in raw_bytes


def test_get_session_items_reflects_confirmed_flag_correctly(temp_db):
    detections = [
        {"id": 0, "page": 1, "label": "PAN", "text": "ABCDE1234F"},
        {"id": 1, "page": 1, "label": "IFSC", "text": "HDFC0001234"},
    ]
    sid = history.log_session("test.pdf", "groq", detections, confirmed_ids={0}, db_path=temp_db)

    items = history.get_session_items(sid, db_path=temp_db)
    pan_item = next(i for i in items if i["label"] == "PAN")
    ifsc_item = next(i for i in items if i["label"] == "IFSC")

    assert pan_item["redacted"] == 1
    assert ifsc_item["redacted"] == 0


def test_get_session_items_empty_for_zero_detection_session(temp_db):
    sid = history.log_session("clean.pdf", "groq", [], confirmed_ids=set(), db_path=temp_db)
    items = history.get_session_items(sid, db_path=temp_db)
    assert items == []
