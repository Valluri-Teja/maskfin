"""
tests/test_rate_limit.py
Tests for the per-session rate limit, including the boundary cases
that are easy to get off-by-one wrong on.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rate_limit import check_rate_limit


def test_allows_first_request_under_limit():
    allowed, msg = check_rate_limit(current_count=0, requested=1, limit=20)
    assert allowed is True
    assert msg == ""


def test_allows_request_exactly_at_limit():
    allowed, msg = check_rate_limit(current_count=15, requested=5, limit=20)
    assert allowed is True


def test_blocks_request_that_would_exceed_limit_by_one():
    allowed, msg = check_rate_limit(current_count=19, requested=2, limit=20)
    assert allowed is False
    assert "20 redactions" in msg


def test_blocks_when_already_at_limit():
    allowed, msg = check_rate_limit(current_count=20, requested=1, limit=20)
    assert allowed is False


def test_batch_request_counted_correctly():
    allowed, msg = check_rate_limit(current_count=15, requested=10, limit=20)
    assert allowed is False
    assert "5 remaining" in msg


def test_zero_requested_always_allowed():
    allowed, msg = check_rate_limit(current_count=20, requested=0, limit=20)
    assert allowed is True


def test_custom_limit_respected():
    allowed, msg = check_rate_limit(current_count=4, requested=2, limit=5)
    assert allowed is False
    assert "5 redactions" in msg
