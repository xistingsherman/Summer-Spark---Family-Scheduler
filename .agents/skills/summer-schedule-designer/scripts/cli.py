"""Command-line interface for the summer schedule planner generator."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from geocode import LAST_RESORT_LAT, LAST_RESORT_LON, LAST_RESORT_NAME, geocode_location
from net import StructuredError
from schedule import DAYS, Profile, calculate_local_attractions, generate_weekly_schedule
from ui import default_template_path, render_schedule_html, write_output
from weather import fetch_weather, neutral_weather

DEFAULT_LOCATION = "El Sereno, Los Angeles, CA"
DEFAULT_OUTPUT_PATH = "summer_schedule.html"
DEFAULT_FIELD_TRIP_DAY = "Friday"

# Matches the reference family this skill was originally built around; used
# only when the caller supplies neither --profiles nor --profiles-file.
DEFAULT_PROFILES: list[Profile] = [
    {"age": 8, "hobbies": ["drawing", "crafts"], "needs": ["reading-remediation", "math-drills"]},
    {"age": 14, "hobbies": ["soccer", "music"], "needs": []},
    {"age": 16, "hobbies": ["coding", "volunteering"], "needs": []},
]


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser with help text for every option."""
    parser = argparse.ArgumentParser(
        description="Generate a custom summer schedule HTML planner.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--location",
        default=DEFAULT_LOCATION,
        help="Home location as city/state (or full address), e.g. 'El Sereno, Los Angeles, CA'.",
    )
    parser.add_argument(
        "--fallback-location",
        default=DEFAULT_LOCATION,
        help="Location to geocode instead if --location fails to resolve.",
    )
    profiles_group = parser.add_mutually_exclusive_group()
    profiles_group.add_argument(
        "--profiles-file",
        help=(
            "Path to a JSON file containing an array of child profiles. "
            'Each profile: {"age": int, "hobbies": [str, ...], "needs": [str, ...]}. '
            "Preferred over --profiles since it avoids shell quoting issues."
        ),
    )
    profiles_group.add_argument(
        "--profiles",
        help=(
            "JSON string of child profiles (same shape as --profiles-file). "
            "Prefer --profiles-file when the JSON is long, since shell quoting "
            "of embedded double quotes is error-prone."
        ),
    )
    parser.add_argument(
        "--field-trip-day",
        default=DEFAULT_FIELD_TRIP_DAY,
        choices=DAYS,
        help="Day of the week for the weekly outing/field trip.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write the generated HTML planner to.",
    )
    return parser


def validate_profiles(raw: Any) -> list[Profile]:
    """Validate and normalize parsed profiles JSON.

    Raises:
        ValueError: If ``raw`` is not a list of profile objects, or a
            profile is missing required fields or has the wrong type,
            with a message identifying which profile and field is at fault.
    """
    if not isinstance(raw, list):
        raise ValueError(f"Profiles must be a JSON array, got {type(raw).__name__}")
    if not raw:
        raise ValueError("Profiles array must not be empty")

    profiles: list[Profile] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Profile at index {index} must be a JSON object, got {type(item).__name__}")

        if "age" not in item:
            raise ValueError(f"Profile at index {index} is missing required field 'age'")
        age = item["age"]
        if not isinstance(age, int) or isinstance(age, bool):
            raise ValueError(f"Profile at index {index} field 'age' must be an integer, got {type(age).__name__}")

        hobbies = item.get("hobbies", [])
        if not isinstance(hobbies, list) or not all(isinstance(h, str) for h in hobbies):
            raise ValueError(f"Profile at index {index} field 'hobbies' must be a list of strings")

        needs = item.get("needs", [])
        if not isinstance(needs, list) or not all(isinstance(n, str) for n in needs):
            raise ValueError(f"Profile at index {index} field 'needs' must be a list of strings")

        profiles.append({"age": age, "hobbies": hobbies, "needs": needs})

    return profiles


def load_profiles(args: argparse.Namespace) -> list[Profile]:
    """Load profiles from --profiles-file, --profiles, or the built-in default.

    Raises:
        ValueError: If the JSON is malformed or fails validation.
        OSError: If --profiles-file cannot be read.
    """
    if args.profiles_file:
        with open(args.profiles_file, encoding="utf-8") as f:
            raw_text = f.read()
        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in --profiles-file '{args.profiles_file}': {exc}") from exc
        return validate_profiles(raw)

    if args.profiles:
        try:
            raw = json.loads(args.profiles)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in --profiles: {exc}") from exc
        return validate_profiles(raw)

    return DEFAULT_PROFILES


def resolve_location(
    location: str, fallback_location: str
) -> tuple[float, float, str, list[StructuredError]]:
    """Geocode ``location``, falling back to ``fallback_location``, then a
    last-resort constant if both fail. Any failure is reported via the
    returned error list rather than silently swallowed.

    Returns:
        ``(lat, lon, display_name, errors)``.
    """
    errors: list[StructuredError] = []

    lat, lon, display_name, error = geocode_location(location)
    if error is None:
        assert lat is not None and lon is not None and display_name is not None
        return lat, lon, display_name, errors

    fb_lat, fb_lon, fb_name, fb_error = geocode_location(fallback_location)
    if fb_error is None:
        assert fb_lat is not None and fb_lon is not None and fb_name is not None
        errors.append(
            {
                "error": "Geocoding failed for requested location",
                "details": (
                    f"Could not geocode '{location}' ({error['details']}). "
                    f"Using fallback location '{fallback_location}' instead."
                ),
            }
        )
        return fb_lat, fb_lon, fb_name, errors

    errors.append(
        {
            "error": "Geocoding failed",
            "details": (
                f"Could not geocode '{location}' ({error['details']}) or fallback "
                f"'{fallback_location}' ({fb_error['details']}). Using approximate coordinates."
            ),
        }
    )
    return LAST_RESORT_LAT, LAST_RESORT_LON, LAST_RESORT_NAME, errors


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: parse arguments, generate the schedule, and write the HTML file."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        profiles = load_profiles(args)
    except (ValueError, OSError) as exc:
        print(f"Error loading profiles: {exc}", file=sys.stderr)
        return 1

    errors: list[StructuredError] = []

    print(f"Geocoding location: {args.location}")
    lat, lon, display_name, geo_errors = resolve_location(args.location, args.fallback_location)
    errors.extend(geo_errors)
    print(f"Resolved coordinates: Lat {lat}, Lon {lon}")

    print("Fetching weather forecast...")
    weather, weather_error = fetch_weather(lat, lon)
    if weather_error is not None:
        errors.append(weather_error)
        weather = neutral_weather()
    assert weather is not None
    print(f"Weather: {weather['temp']}°F, {weather['description']}. Advice: {weather['advice']}")

    for err in errors:
        print(f"Warning: {err['error']} - {err['details']}", file=sys.stderr)

    print("Calculating distances to attractions...")
    is_la = "Los Angeles" in display_name or "CA" in display_name or "Sereno" in display_name
    attractions = calculate_local_attractions(lat, lon, is_la)
    print(f"Found {len(attractions)} local attractions.")

    print(f"Generating weekly schedule (field trip day: {args.field_trip_day})...")
    schedule = generate_weekly_schedule(profiles, weather, field_trip_day=args.field_trip_day)

    try:
        html_content = render_schedule_html(
            schedule=schedule,
            weather=weather,
            attractions=attractions,
            profiles=profiles,
            location_name=display_name,
            errors=errors,
            template_path=default_template_path(),
        )
        output_path = write_output(html_content, args.output)
    except OSError as exc:
        print(f"Error writing schedule HTML: {exc}", file=sys.stderr)
        return 1

    print(f"Success! Generated summer schedule HTML at: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
