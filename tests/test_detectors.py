"""
tests/test_detectors.py
Unit tests for the individual detection building blocks: Luhn
validation, regex patterns in isolation, and edge cases the
document-level eval harness (eval_accuracy.py) doesn't specifically
target (empty strings, malformed input, boundary formats).

Run with: pytest tests/test_detectors.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from detectors import _luhn_check, PATTERNS


def test_luhn_accepts_known_valid_visa():
    assert _luhn_check("4111111111111111") is True


def test_luhn_accepts_known_valid_mastercard():
    assert _luhn_check("5500000000000004") is True


def test_luhn_rejects_sequential_digits():
    assert _luhn_check("1234567890123456") is False


def test_luhn_rejects_repeated_digits():
    assert _luhn_check("9999999999999999") is False


def test_luhn_rejects_too_short_input():
    assert _luhn_check("1234") is False


def test_luhn_rejects_empty_string():
    assert _luhn_check("") is False


def test_luhn_handles_spaced_input():
    assert _luhn_check("4111 1111 1111 1111") is True


def test_luhn_handles_dashed_input():
    assert _luhn_check("4111-1111-1111-1111") is True


def test_luhn_rejects_non_numeric_garbage():
    assert _luhn_check("abcd-efgh-ijkl-mnop") is False


def _pattern_for(label):
    return next(p for l, p, v in PATTERNS if l == label)


def test_pan_pattern_matches_valid_format():
    assert _pattern_for("PAN").search("ABCDE1234F") is not None


def test_pan_pattern_rejects_wrong_length():
    assert _pattern_for("PAN").fullmatch("ABCDE1234") is None


def test_pan_pattern_rejects_all_digits():
    assert _pattern_for("PAN").fullmatch("1234567890") is None


def test_gstin_pattern_matches_valid_format():
    assert _pattern_for("GSTIN").search("27AAAAA0000A1Z5") is not None


def test_gstin_pattern_rejects_missing_z():
    assert _pattern_for("GSTIN").fullmatch("27AAAAA0000A1X5") is None


def test_aadhaar_pattern_matches_with_spaces():
    assert _pattern_for("Aadhaar").search("1234 5678 9012") is not None


def test_aadhaar_pattern_matches_without_spaces():
    assert _pattern_for("Aadhaar").search("123456789012") is not None


def test_phone_pattern_rejects_landline_prefix():
    assert _pattern_for("Phone Number").fullmatch("5876543210") is None


def test_phone_pattern_accepts_plus91_prefix():
    m = _pattern_for("Phone Number").search("+91 9876543210")
    assert m is not None


def test_email_pattern_rejects_missing_at_symbol():
    assert _pattern_for("Email").search("not.an.email.example.com") is None


def test_email_pattern_matches_standard_format():
    assert _pattern_for("Email").search("user.name+tag@example.co.in") is not None


def test_passport_pattern_matches_standard_format():
    assert _pattern_for("Passport").search("A1234567") is not None


def test_ifsc_pattern_requires_zero_at_position_5():
    assert _pattern_for("IFSC").fullmatch("HDFC1001234") is None
    assert _pattern_for("IFSC").fullmatch("HDFC0001234") is not None
