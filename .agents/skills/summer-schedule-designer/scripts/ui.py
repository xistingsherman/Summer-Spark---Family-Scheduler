"""Render the schedule data into the standalone HTML planner."""

from __future__ import annotations

import json
import os
from typing import Any

from net import StructuredError
from schedule import Attraction, Profile
from weather import WeatherResult

TEMPLATE_RELATIVE_PATH = os.path.join("..", "resources", "template.html")


def render_schedule_html(
    *,
    schedule: dict[str, dict[str, list[dict[str, Any]]]],
    weather: WeatherResult,
    attractions: list[Attraction],
    profiles: list[Profile],
    location_name: str,
    errors: list[StructuredError],
    template_path: str,
) -> str:
    """Fill the HTML template's placeholders with the generated data.

    Raises:
        FileNotFoundError: If ``template_path`` does not exist.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at {template_path}")

    with open(template_path, encoding="utf-8") as f:
        html_content = f.read()

    replacements = {
        "{{SCHEDULE_DATA_JSON}}": json.dumps(schedule, indent=4),
        "{{WEATHER_DATA_JSON}}": json.dumps(weather, indent=4),
        "{{ATTRACTION_DATA_JSON}}": json.dumps(attractions, indent=4),
        "{{CHILD_PROFILES_JSON}}": json.dumps(profiles, indent=4),
        "{{LOCATION_NAME}}": location_name,
        "{{ERRORS_JSON}}": json.dumps(errors, indent=4),
    }
    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, value)

    return html_content


def write_output(html_content: str, output_path: str) -> str:
    """Write the rendered HTML to ``output_path`` and return its absolute path."""
    absolute_path = os.path.abspath(output_path)
    with open(absolute_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return absolute_path


def default_template_path() -> str:
    """Return the path to the bundled template.html relative to this file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, TEMPLATE_RELATIVE_PATH)
