"""Tests for geocode.py, mocking urllib.request.urlopen."""

import json
from unittest.mock import MagicMock, patch

import geocode


def _mock_response(payload):
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    return mock_resp


def test_geocode_location_success():
    payload = [{"lat": "34.07", "lon": "-118.19", "display_name": "El Sereno, Los Angeles, CA"}]
    with patch("geocode.urllib.request.urlopen", return_value=_mock_response(payload)):
        lat, lon, name, error = geocode.geocode_location("El Sereno, Los Angeles, CA")

    assert lat == 34.07
    assert lon == -118.19
    assert name == "El Sereno, Los Angeles, CA"
    assert error is None


def test_geocode_location_no_results_returns_structured_error():
    with patch("geocode.urllib.request.urlopen", return_value=_mock_response([])):
        lat, lon, name, error = geocode.geocode_location("Nowhereville")

    assert lat is None
    assert lon is None
    assert name is None
    assert error["error"] == "Geocoding failed"
    assert "Nowhereville" in error["details"]


def test_geocode_location_network_failure_retries_then_reports_error():
    with (
        patch("geocode.urllib.request.urlopen", side_effect=OSError("network down")),
        patch("net.time.sleep"),
    ):
        lat, lon, name, error = geocode.geocode_location("Somewhere", retries=2, backoff_seconds=0.01)

    assert lat is None
    assert error["error"] == "Geocoding failed"
    assert "network down" in error["details"]
