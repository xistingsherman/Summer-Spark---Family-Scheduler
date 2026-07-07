"""Tests for weather.py, mocking urllib.request.urlopen."""

import json
from unittest.mock import MagicMock, patch

import weather


def _mock_response(payload):
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    return mock_resp


def test_translate_weather_code_known_codes():
    assert weather.translate_weather_code(0) == ("Clear Sky", "☀️")
    assert weather.translate_weather_code(61) == ("Rainy", "🌧️")
    assert weather.translate_weather_code(999) == ("Cloudy", "☁️")


def test_fetch_weather_hot_day():
    payload = {"daily": {"temperature_2m_max": [95], "temperature_2m_min": [70], "weathercode": [1]}}
    with patch("weather.urllib.request.urlopen", return_value=_mock_response(payload)):
        result, error = weather.fetch_weather(34.0, -118.0)

    assert error is None
    assert result["is_hot"] is True
    assert result["temp"] == 95
    assert "hot" in result["advice"].lower()


def test_fetch_weather_rainy_day():
    payload = {"daily": {"temperature_2m_max": [75], "temperature_2m_min": [60], "weathercode": [61]}}
    with patch("weather.urllib.request.urlopen", return_value=_mock_response(payload)):
        result, error = weather.fetch_weather(34.0, -118.0)

    assert error is None
    assert result["is_rainy"] is True


def test_fetch_weather_missing_daily_key_reports_error():
    with patch("weather.urllib.request.urlopen", return_value=_mock_response({})):
        result, error = weather.fetch_weather(34.0, -118.0)

    assert result is None
    assert error["error"] == "Weather fetch failed"


def test_fetch_weather_network_failure_reports_structured_error():
    with (
        patch("weather.urllib.request.urlopen", side_effect=OSError("timeout")),
        patch("net.time.sleep"),
    ):
        result, error = weather.fetch_weather(34.0, -118.0, retries=2, backoff_seconds=0.01)

    assert result is None
    assert error["error"] == "Weather fetch failed"
    assert "timeout" in error["details"]


def test_neutral_weather_is_never_flagged_as_hot_or_rainy():
    neutral = weather.neutral_weather()
    assert neutral["is_hot"] is False
    assert neutral["is_rainy"] is False
