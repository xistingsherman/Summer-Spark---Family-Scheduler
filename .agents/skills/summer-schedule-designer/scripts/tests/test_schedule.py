"""Tests for schedule.py: distance math, attractions, and schedule generation."""

import pytest

import schedule


def test_haversine_same_point_is_zero():
    assert schedule.haversine(34.0, -118.0, 34.0, -118.0) == 0


def test_haversine_known_distance_la_to_sf():
    distance = schedule.haversine(34.0522, -118.2437, 37.7749, -122.4194)
    assert 340 < distance < 360


def test_calculate_local_attractions_la_sorted_by_distance():
    attractions = schedule.calculate_local_attractions(34.0722, -118.1883, is_la=True)
    distances = [a["distance"] for a in attractions]
    assert distances == sorted(distances)
    assert attractions[0]["name"] == "Ascot Hills Park"


def test_calculate_local_attractions_generic_when_not_la():
    attractions = schedule.calculate_local_attractions(40.0, -75.0, is_la=False)
    assert len(attractions) == len(schedule.GENERIC_ATTRACTIONS)
    distances = [a["distance"] for a in attractions]
    assert distances == sorted(distances)


def test_generate_weekly_schedule_has_all_days_and_time_blocks():
    profiles = [{"age": 8, "hobbies": [], "needs": []}]
    weather_data = {"is_hot": False, "is_rainy": False}

    result = schedule.generate_weekly_schedule(profiles, weather_data)

    assert set(result.keys()) == {
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    }
    for blocks in result.values():
        assert set(blocks.keys()) == {"Morning", "Afternoon", "Evening"}


def test_generate_weekly_schedule_reading_remediation_need():
    profiles = [{"age": 8, "hobbies": [], "needs": ["reading-remediation"]}]
    weather_data = {"is_hot": False, "is_rainy": False}

    result = schedule.generate_weekly_schedule(profiles, weather_data)

    monday_titles = [item["title"] for item in result["Monday"]["Morning"]]
    assert "Guided Reading Practice" in monday_titles


def test_generate_weekly_schedule_hot_weather_uses_pool_or_library():
    profiles = [{"age": 8, "hobbies": [], "needs": []}]
    weather_data = {"is_hot": True, "is_rainy": False}

    result = schedule.generate_weekly_schedule(profiles, weather_data)

    tuesday_titles = [item["title"] for item in result["Tuesday"]["Afternoon"]]
    assert "Belvedere Pool Swim" in tuesday_titles


def test_generate_weekly_schedule_field_trip_day_is_configurable():
    profiles = [{"age": 8, "hobbies": [], "needs": []}]
    weather_data = {"is_hot": False, "is_rainy": False}

    result = schedule.generate_weekly_schedule(profiles, weather_data, field_trip_day="Monday")

    monday_tags = [item["tag"] for item in result["Monday"]["Morning"] + result["Monday"]["Afternoon"]]
    friday_tags = [item["tag"] for item in result["Friday"]["Morning"] + result["Friday"]["Afternoon"]]
    assert "Field Trip" in monday_tags
    assert "Field Trip" not in friday_tags


def test_generate_weekly_schedule_rejects_invalid_field_trip_day():
    profiles = [{"age": 8, "hobbies": [], "needs": []}]
    weather_data = {"is_hot": False, "is_rainy": False}

    with pytest.raises(ValueError, match="field_trip_day"):
        schedule.generate_weekly_schedule(profiles, weather_data, field_trip_day="Someday")


def test_get_age_band_covers_all_ages():
    assert schedule.get_age_band(3) == "early_childhood"
    assert schedule.get_age_band(6) == "early_childhood"
    assert schedule.get_age_band(7) == "elementary"
    assert schedule.get_age_band(9) == "elementary"
    assert schedule.get_age_band(10) == "tween"
    assert schedule.get_age_band(12) == "tween"
    assert schedule.get_age_band(13) == "teen"
    assert schedule.get_age_band(15) == "teen"
    assert schedule.get_age_band(16) == "older_teen"
    assert schedule.get_age_band(17) == "older_teen"


def test_five_year_old_gets_age_appropriate_activities_not_silent_reading():
    profiles = [{"age": 5, "hobbies": [], "needs": []}]
    weather_data = {"is_hot": False, "is_rainy": False}

    result = schedule.generate_weekly_schedule(profiles, weather_data)

    monday_afternoon_titles = [item["title"] for item in result["Monday"]["Afternoon"]]
    assert "Quiet Silent Reading" not in monday_afternoon_titles
    assert "Quiet Time & Picture Books" in monday_afternoon_titles
    assert "Quiet Reading Time" not in monday_afternoon_titles

    monday_morning_titles = [item["title"] for item in result["Monday"]["Morning"]]
    assert "Sensory & Motor Play" in monday_morning_titles

    evening_titles = [item["title"] for item in result["Monday"]["Evening"]]
    assert "Wind-down Reading" in evening_titles
    assert "Tween/Teen Relaxation" not in evening_titles


def test_children_of_different_ages_get_different_schedules():
    profiles = [
        {"age": 5, "hobbies": [], "needs": []},
        {"age": 14, "hobbies": ["soccer"], "needs": []},
    ]
    weather_data = {"is_hot": False, "is_rainy": False}

    result = schedule.generate_weekly_schedule(profiles, weather_data)

    def titles_for_age(day, block, age):
        return [item["title"] for item in result[day][block] if age in item.get("kids", [])]

    five_year_old_afternoon = titles_for_age("Monday", "Afternoon", 5)
    teen_afternoon = titles_for_age("Monday", "Afternoon", 14)
    assert five_year_old_afternoon != teen_afternoon
    assert "Sensory Bin & Simple Crafts" in five_year_old_afternoon
    assert "Soccer Practice" in titles_for_age("Monday", "Morning", 14)
    assert "Sensory & Motor Play" in titles_for_age("Monday", "Morning", 5)


def test_generate_weekly_schedule_flags_flexible_afternoon_activities_as_shuffleable():
    profiles = [{"age": 8, "hobbies": [], "needs": []}]
    weather_data = {"is_hot": False, "is_rainy": False}

    result = schedule.generate_weekly_schedule(profiles, weather_data)

    monday_shuffleable = [item for item in result["Monday"]["Afternoon"] if item.get("shuffleable")]
    tuesday_shuffleable = [item for item in result["Tuesday"]["Afternoon"] if item.get("shuffleable")]
    friday_shuffleable = [item for item in result["Friday"]["Afternoon"] if item.get("shuffleable")]
    assert monday_shuffleable
    assert tuesday_shuffleable
    assert friday_shuffleable == []  # field trip day is never shuffleable

    # The fixed evening-adjacent reading block is never shuffleable.
    monday_titles_not_shuffleable = [
        item["title"] for item in result["Monday"]["Afternoon"] if not item.get("shuffleable")
    ]
    assert "Quiet Reading Time" in monday_titles_not_shuffleable
