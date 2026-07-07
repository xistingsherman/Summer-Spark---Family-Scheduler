"""Shared network helpers: retry with exponential backoff and structured errors."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypedDict, TypeVar

T = TypeVar("T")


class StructuredError(TypedDict):
    """A user-facing error the UI can render instead of a raw traceback."""

    error: str
    details: str


def fetch_with_retry(
    fetch: Callable[[], T],
    *,
    retries: int = 3,
    backoff_seconds: float = 0.5,
    error_label: str = "Request failed",
) -> tuple[T | None, StructuredError | None]:
    """Call ``fetch()``, retrying with exponential backoff if it raises.

    Args:
        fetch: A zero-argument callable that performs the network call and
            returns a parsed result, raising on failure.
        retries: Maximum number of attempts before giving up.
        backoff_seconds: Base delay between attempts; doubles each retry.
        error_label: Short label used in the structured error on failure.

    Returns:
        ``(result, None)`` on success, or ``(None, error)`` once all
        retries are exhausted. Never raises.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return fetch(), None
        except Exception as exc:  # noqa: BLE001 - any failure here should trigger a retry
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff_seconds * (2**attempt))
    return None, {"error": error_label, "details": str(last_exc)}
