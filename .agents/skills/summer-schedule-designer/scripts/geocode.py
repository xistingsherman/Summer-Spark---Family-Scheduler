"""Resolve free-text locations to coordinates via the Nominatim API."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from net import StructuredError, fetch_with_retry

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SummerSchedulePlannerAgent/1.0"

# Absolute last resort used only if both the requested location and the
# user-supplied fallback location fail to geocode after retries. Any use of
# these coordinates is always reported back via the returned StructuredError
# so the caller can surface it rather than silently pretending it's real.
LAST_RESORT_LAT = 34.0722
LAST_RESORT_LON = -118.1883
LAST_RESORT_NAME = "El Sereno, Los Angeles, CA (approximate, geocoding unavailable)"


def geocode_location(
    location: str,
    *,
    retries: int = 3,
    backoff_seconds: float = 0.5,
) -> tuple[float | None, float | None, str | None, StructuredError | None]:
    """Resolve ``location`` to coordinates using the Nominatim search API.

    Args:
        location: Free-text location, e.g. "El Sereno, Los Angeles, CA".
        retries: Number of attempts before giving up.
        backoff_seconds: Base delay between retries; doubles each attempt.

    Returns:
        ``(lat, lon, display_name, None)`` on success, or
        ``(None, None, None, error)`` if geocoding fails after retries or
        returns no results.
    """
    encoded_location = urllib.parse.quote(location)
    url = f"{NOMINATIM_URL}?q={encoded_location}&format=json&limit=1"

    def _request() -> list:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    data, error = fetch_with_retry(
        _request,
        retries=retries,
        backoff_seconds=backoff_seconds,
        error_label="Geocoding failed",
    )
    if error is not None:
        return None, None, None, error
    if not data:
        return (
            None,
            None,
            None,
            {"error": "Geocoding failed", "details": f"No results found for '{location}'"},
        )

    result = data[0]
    return float(result["lat"]), float(result["lon"]), result["display_name"], None
