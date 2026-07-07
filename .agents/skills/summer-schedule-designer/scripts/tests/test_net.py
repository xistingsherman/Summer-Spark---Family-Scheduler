"""Tests for the retry-with-backoff helper in net.py."""

from unittest.mock import patch

import net


def test_fetch_with_retry_succeeds_first_try():
    result, error = net.fetch_with_retry(lambda: 42)
    assert result == 42
    assert error is None


def test_fetch_with_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("boom")
        return "ok"

    with patch("net.time.sleep") as mock_sleep:
        result, error = net.fetch_with_retry(flaky, retries=3, backoff_seconds=0.01)

    assert result == "ok"
    assert error is None
    assert mock_sleep.call_count == 2


def test_fetch_with_retry_exhausts_retries_and_returns_structured_error():
    def always_fails():
        raise ValueError("nope")

    with patch("net.time.sleep"):
        result, error = net.fetch_with_retry(
            always_fails, retries=2, backoff_seconds=0.01, error_label="Custom failure"
        )

    assert result is None
    assert error == {"error": "Custom failure", "details": "nope"}
