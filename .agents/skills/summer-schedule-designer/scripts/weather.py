"""Fetch daily weather forecasts and translate them into scheduling advice."""

from __future__ import annotations

import json
import urllib.request
from typing import TypedDict

from net import StructuredError, fetch_with_retry

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Neutral assumptions used only to keep schedule generation functional when
# the live forecast is unavailable. These are never presented to the user as
# real weather data - any failure is surfaced separately via StructuredError.
NEUTRAL_TEMP = 84
NEUTRAL_DESCRIPTION = "Unknown (forecast unavailable)"
NEUTRAL_ICON = "❓"
NEUTRAL_ADVICE = (
    "We couldn't fetch a live forecast, so this schedule assumes typical "
    "summer weather. Balance outdoor play in the morning with indoor "
    "educational study in the afternoon."
)


class WeatherResult(TypedDict):
    """Weather summary used to drive schedule generation and UI display."""

    temp: int
    description: str
    icon: str
    advice: str
    is_hot: bool
    is_rainy: bool


def translate_weather_code(code: int) -> tuple[str, str]:
    """Map an Open-Meteo WMO weather code to a human description and emoji."""
    if code == 0:
        return "Clear Sky", "☀️"
    if code in (1, 2, 3):
        return "Mainly Clear / Partly Cloudy", "⛅"
    if code in (45, 48):
        return "Foggy", "🌫️"
    if code in (51, 53, 55):
        return "Drizzle", "🌧️"
    if code in (61, 63, 65):
        return "Rainy", "🌧️"
    if code in (71, 73, 75):
        return "Snowy", "❄️"
    if code in (80, 81, 82):
        return "Rain Showers", "🌦️"
    if code in (95, 96, 99):
        return "Thunderstorm", "⛈️"
    return "Cloudy", "☁️"


def fetch_weather(
    lat: float,
    lon: float,
    *,
    retries: int = 3,
    backoff_seconds: float = 0.5,
) -> tuple[WeatherResult | None, StructuredError | None]:
    """Fetch today's forecast for ``(lat, lon)`` and derive scheduling advice.

    Args:
        lat: Latitude of the target location.
        lon: Longitude of the target location.
        retries: Number of attempts before giving up.
        backoff_seconds: Base delay between retries; doubles each attempt.

    Returns:
        ``(weather, None)`` on success, or ``(None, error)`` if the forecast
        cannot be fetched or parsed after retries.
    """
    url = (
        f"{FORECAST_URL}?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,weathercode"
        "&timezone=auto&temperature_unit=fahrenheit"
    )

    def _request() -> dict:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    data, error = fetch_with_retry(
        _request,
        retries=retries,
        backoff_seconds=backoff_seconds,
        error_label="Weather fetch failed",
    )
    if error is not None:
        return None, error
    assert data is not None  # fetch_with_retry guarantees data xor error
    if "daily" not in data:
        return None, {
            "error": "Weather fetch failed",
            "details": "Forecast response did not include daily data",
        }

    temp_max = data["daily"]["temperature_2m_max"][0]
    weather_code = data["daily"]["weathercode"][0]
    description, icon = translate_weather_code(weather_code)
    is_hot = temp_max > 88
    is_rainy = weather_code >= 50

    if is_hot:
        advice = (
            f"Warning: Very hot day forecast ({temp_max}°F)! Focus on indoor "
            "reading, worksheets, library visits, or swimming pools during "
            "the hot afternoon hours."
        )
    elif temp_max < 70:
        advice = f"Mild day forecast ({temp_max}°F). Excellent for outdoor hikes, park sports, and physical play."
    elif is_rainy:
        advice = "Rain or showers expected. Focus on indoor activities: worksheets, board games, library, or museum visits."
    else:
        advice = "Perfect summer weather! Balance outdoor activities in the morning and educational study in the afternoon."

    return (
        {
            "temp": round(temp_max),
            "description": description,
            "icon": icon,
            "advice": advice,
            "is_hot": is_hot,
            "is_rainy": is_rainy,
        },
        None,
    )


def neutral_weather() -> WeatherResult:
    """Return the neutral weather assumption used when the forecast fails."""
    return {
        "temp": NEUTRAL_TEMP,
        "description": NEUTRAL_DESCRIPTION,
        "icon": NEUTRAL_ICON,
        "advice": NEUTRAL_ADVICE,
        "is_hot": False,
        "is_rainy": False,
    }
