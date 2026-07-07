"""Tests for cli.py: argument parsing, profile validation, and main()."""

import json
from unittest.mock import patch

import pytest

import cli


def test_build_arg_parser_defaults():
    parser = cli.build_arg_parser()
    args = parser.parse_args([])
    assert args.location == cli.DEFAULT_LOCATION
    assert args.fallback_location == cli.DEFAULT_LOCATION
    assert args.profiles is None
    assert args.profiles_file is None
    assert args.output == cli.DEFAULT_OUTPUT_PATH
    assert args.field_trip_day == cli.DEFAULT_FIELD_TRIP_DAY


def test_field_trip_day_accepts_valid_day():
    parser = cli.build_arg_parser()
    args = parser.parse_args(["--field-trip-day", "Monday"])
    assert args.field_trip_day == "Monday"


def test_field_trip_day_rejects_invalid_day():
    parser = cli.build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--field-trip-day", "Someday"])


def test_profiles_and_profiles_file_are_mutually_exclusive():
    parser = cli.build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--profiles", "[]", "--profiles-file", "x.json"])


def test_validate_profiles_success():
    raw = [{"age": 8, "hobbies": ["a"], "needs": []}]
    assert cli.validate_profiles(raw) == raw


def test_validate_profiles_defaults_missing_hobbies_and_needs():
    result = cli.validate_profiles([{"age": 8}])
    assert result == [{"age": 8, "hobbies": [], "needs": []}]


def test_validate_profiles_rejects_non_list():
    with pytest.raises(ValueError, match="must be a JSON array"):
        cli.validate_profiles({"age": 8})


def test_validate_profiles_rejects_empty_list():
    with pytest.raises(ValueError, match="must not be empty"):
        cli.validate_profiles([])


def test_validate_profiles_missing_age():
    with pytest.raises(ValueError, match="missing required field 'age'"):
        cli.validate_profiles([{"hobbies": []}])


def test_validate_profiles_wrong_type_age():
    with pytest.raises(ValueError, match="must be an integer"):
        cli.validate_profiles([{"age": "eight"}])


def test_validate_profiles_wrong_type_hobbies():
    with pytest.raises(ValueError, match="must be a list of strings"):
        cli.validate_profiles([{"age": 8, "hobbies": "drawing"}])


def test_load_profiles_from_profiles_string():
    args = cli.build_arg_parser().parse_args(["--profiles", json.dumps([{"age": 8}])])
    assert cli.load_profiles(args) == [{"age": 8, "hobbies": [], "needs": []}]


def test_load_profiles_from_file(tmp_path):
    profiles_file = tmp_path / "profiles.json"
    profiles_file.write_text(json.dumps([{"age": 14, "hobbies": ["soccer"], "needs": []}]))
    args = cli.build_arg_parser().parse_args(["--profiles-file", str(profiles_file)])
    assert cli.load_profiles(args)[0]["age"] == 14


def test_load_profiles_invalid_json_string_raises_clear_error():
    args = cli.build_arg_parser().parse_args(["--profiles", "{not valid json"])
    with pytest.raises(ValueError, match="Invalid JSON"):
        cli.load_profiles(args)


def test_load_profiles_default_when_none_given():
    args = cli.build_arg_parser().parse_args([])
    assert cli.load_profiles(args) == cli.DEFAULT_PROFILES


def test_resolve_location_success_has_no_errors():
    with patch("cli.geocode_location", return_value=(1.0, 2.0, "Somewhere", None)):
        lat, lon, name, errors = cli.resolve_location("Somewhere", "Fallback")
    assert (lat, lon, name) == (1.0, 2.0, "Somewhere")
    assert errors == []


def test_resolve_location_falls_back_and_reports_error():
    def fake_geocode(location, **kwargs):
        if location == "Bad":
            return None, None, None, {"error": "Geocoding failed", "details": "no results"}
        return 3.0, 4.0, "Fallback City", None

    with patch("cli.geocode_location", side_effect=fake_geocode):
        lat, lon, name, errors = cli.resolve_location("Bad", "Fallback")

    assert (lat, lon, name) == (3.0, 4.0, "Fallback City")
    assert len(errors) == 1
    assert "Bad" in errors[0]["details"]


def test_resolve_location_all_fail_uses_last_resort_and_reports_error():
    def fake_geocode(location, **kwargs):
        return None, None, None, {"error": "Geocoding failed", "details": f"{location} down"}

    with patch("cli.geocode_location", side_effect=fake_geocode):
        lat, lon, name, errors = cli.resolve_location("Bad", "AlsoBad")

    assert lat == cli.LAST_RESORT_LAT
    assert lon == cli.LAST_RESORT_LON
    assert name == cli.LAST_RESORT_NAME
    assert len(errors) == 1


def test_main_end_to_end_writes_html(tmp_path):
    output_file = tmp_path / "out.html"
    fake_weather = {
        "temp": 80,
        "description": "Clear",
        "icon": "☀️",
        "advice": "Nice day",
        "is_hot": False,
        "is_rainy": False,
    }

    with (
        patch("cli.geocode_location", return_value=(34.0, -118.0, "Test City, CA", None)),
        patch("cli.fetch_weather", return_value=(fake_weather, None)),
    ):
        exit_code = cli.main(["--output", str(output_file)])

    assert exit_code == 0
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "Test City, CA" in content
    assert "{{" not in content


def test_main_reports_error_and_exits_nonzero_on_bad_profiles(tmp_path):
    output_file = tmp_path / "out.html"
    exit_code = cli.main(["--profiles", "not json", "--output", str(output_file)])
    assert exit_code == 1
    assert not output_file.exists()
