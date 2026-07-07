"""Distance calculations, local attractions, and weekly schedule generation."""

from __future__ import annotations

import math
from typing import Any, TypedDict

from weather import WeatherResult


class Profile(TypedDict):
    """A single child's profile used to tailor the generated schedule."""

    age: int
    hobbies: list[str]
    needs: list[str]


class Attraction(TypedDict):
    """A nearby attraction annotated with its distance from home."""

    name: str
    type: str
    setting: str
    suitability: str
    distance: float


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in miles between two coordinates."""
    lat1_r, lon1_r, lat2_r, lon2_r = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2_r - lon1_r
    dlat = lat2_r - lat1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    earth_radius_miles = 3956
    return c * earth_radius_miles


# Predefined premium attractions in Los Angeles (useful for El Sereno)
LA_ATTRACTIONS: list[dict[str, Any]] = [
    {"name": "Ascot Hills Park", "lat": 34.0722, "lon": -118.1883, "type": "Nature & Hiking (Physical)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
    {"name": "El Sereno Recreation Center", "lat": 34.0744, "lon": -118.1752, "type": "Park & Sports (Physical)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
    {"name": "Huntington Library & Botanical Gardens", "lat": 34.1290, "lon": -118.1145, "type": "Gardens & Museum (Educational)", "setting": "🏛️ Indoor/Outdoor", "suitability": "All Ages"},
    {"name": "Norton Simon Museum", "lat": 34.1460, "lon": -118.1601, "type": "Art Museum (Educational)", "setting": "🏛️ Indoor", "suitability": "Teens Focus"},
    {"name": "Kidspace Children's Museum", "lat": 34.1478, "lon": -118.1678, "type": "Children's Museum (Educational)", "setting": "🏛️ Indoor/Outdoor", "suitability": "8yo Focus"},
    {"name": "Griffith Observatory", "lat": 34.1186, "lon": -118.3004, "type": "Space Observatory (Educational)", "setting": "🏛️ Indoor/Outdoor", "suitability": "All Ages"},
    {"name": "California Science Center", "lat": 34.0159, "lon": -118.2858, "type": "Science Museum (Educational)", "setting": "🏛️ Indoor", "suitability": "All Ages"},
    {"name": "Natural History Museum of LA", "lat": 34.0185, "lon": -118.2882, "type": "History Museum (Educational)", "setting": "🏛️ Indoor", "suitability": "All Ages"},
    {"name": "LA State Historic Park", "lat": 34.0664, "lon": -118.2326, "type": "State Park (Physical)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
    {"name": "Eaton Canyon Nature Center", "lat": 34.1795, "lon": -118.0967, "type": "Hiking & Waterfall (Physical)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
    {"name": "Belvedere Community Regional Park Pool", "lat": 34.0384, "lon": -118.1673, "type": "Swimming Pool (Physical)", "setting": "🌳 Outdoor Pool", "suitability": "All Ages"},
    {"name": "Lacy Park", "lat": 34.1194, "lon": -118.1278, "type": "Scenic Park (Physical)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
]

GENERIC_ATTRACTIONS: list[dict[str, Any]] = [
    {"name": "Local Public Library", "type": "Reading & Study (Educational)", "setting": "🏛️ Indoor (AC)", "suitability": "All Ages"},
    {"name": "Community Pool / YMCA", "type": "Swimming & Recreation (Physical)", "setting": "🌳 Outdoor/Indoor", "suitability": "All Ages"},
    {"name": "State Park & Hiking Trails", "type": "Nature & Hiking (Physical)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
    {"name": "Local Science Museum", "type": "Museum & Science (Educational)", "setting": "🏛️ Indoor", "suitability": "All Ages"},
    {"name": "Community Recreation Park", "type": "Sports & Playgrounds (Physical)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
    {"name": "Botanical Gardens", "type": "Nature & Learning (Educational)", "setting": "🌳 Outdoor", "suitability": "All Ages"},
    {"name": "Art Museum", "type": "Arts & Creative (Educational)", "setting": "🏛️ Indoor", "suitability": "Teens Focus"},
]


def calculate_local_attractions(lat: float, lon: float, is_la: bool) -> list[Attraction]:
    """Build a distance-sorted list of nearby attractions.

    Uses real coordinates (and thus real haversine distances) for LA-area
    homes, and a generic curated list with placeholder distances otherwise.
    """
    attractions: list[Attraction] = []
    if is_la:
        for item in LA_ATTRACTIONS:
            distance = haversine(lat, lon, item["lat"], item["lon"])
            attractions.append(
                {
                    "name": item["name"],
                    "type": item["type"],
                    "setting": item["setting"],
                    "suitability": item["suitability"],
                    "distance": distance,
                }
            )
    else:
        for i, item in enumerate(GENERIC_ATTRACTIONS):
            attractions.append(
                {
                    "name": item["name"],
                    "type": item["type"],
                    "setting": item["setting"],
                    "suitability": item["suitability"],
                    "distance": 1.5 + i * 1.2,
                }
            )
    attractions.sort(key=lambda x: x["distance"])
    return attractions


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_age_band(age: int) -> str:
    """Classify an age into the developmental band used to pick activities.

    Bands: "early_childhood" (<=6), "elementary" (7-9), "tween" (10-12),
    "teen" (13-15), "older_teen" (16+). Every age maps to exactly one band,
    so every child gets age-appropriate, individualized activities rather
    than falling back to only the shared family blocks.
    """
    if age <= 6:
        return "early_childhood"
    if age <= 9:
        return "elementary"
    if age <= 12:
        return "tween"
    if age <= 15:
        return "teen"
    return "older_teen"


def generate_weekly_schedule(
    profiles: list[Profile],
    weather: WeatherResult,
    field_trip_day: str = "Friday",
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Build a Monday-Sunday schedule tailored to ``profiles`` and ``weather``.

    Args:
        profiles: Child profiles to tailor activities to.
        weather: Forecast summary used to pick indoor/outdoor activities.
        field_trip_day: Day of the week for the weekly outing/field trip.
            Must be one of ``DAYS``.

    Activities are chosen per child using ``get_age_band``, so every age gets
    individualized morning/afternoon/evening blocks (not just ages 8/14/16).
    """
    if field_trip_day not in DAYS:
        raise ValueError(f"field_trip_day must be one of {DAYS}, got {field_trip_day!r}")

    days = DAYS
    schedule: dict[str, dict[str, list[dict[str, Any]]]] = {
        day: {"Morning": [], "Afternoon": [], "Evening": []} for day in days
    }

    ages = [p["age"] for p in profiles]
    is_hot = weather.get("is_hot", False)
    is_rainy = weather.get("is_rainy", False)

    for day in days:
        # --- MORNING BLOCK ---
        if day == field_trip_day:
            schedule[day]["Morning"].append(
                {
                    "time": "9:30 AM - 12:00 PM",
                    "category": "other",
                    "emoji": "🚗",
                    "tag": "Field Trip",
                    "title": "Friday Day Out: Morning Outing",
                    "desc": "Pack snacks and head out! Weekly rotation suggestion: Week 1: California Science Center; Week 2: Griffith Observatory & Hike; Week 3: Huntington Gardens; Week 4: La Brea Tar Pits.",
                    "kids": ages,
                }
            )
        elif is_rainy:
            schedule[day]["Morning"].append(
                {
                    "time": "9:00 AM - 10:30 AM",
                    "category": "edu",
                    "emoji": "📚",
                    "tag": "Educational",
                    "title": "Academic Core",
                    "desc": "Summer reading & core workbook exercises",
                    "kids": ages,
                }
            )
            schedule[day]["Morning"].append(
                {
                    "time": "10:30 AM - 11:30 AM",
                    "category": "other",
                    "emoji": "🎲",
                    "tag": "Creative",
                    "title": "Indoor Play & Games",
                    "desc": "Board games, coloring sheets, or Lego",
                    "kids": ages,
                }
            )
        else:
            schedule[day]["Morning"].append(
                {
                    "time": "8:30 AM - 9:30 AM",
                    "category": "phys",
                    "emoji": "🌳",
                    "tag": "Physical",
                    "title": "Family Morning Walk",
                    "desc": "Walk/jog at Ascot Hills Park",
                    "kids": ages,
                }
            )

            for p in profiles:
                age = p["age"]
                hobs = p.get("hobbies", [])
                band = get_age_band(age)
                if band == "early_childhood":
                    schedule[day]["Morning"].append(
                        {
                            "time": "9:30 AM - 10:15 AM",
                            "category": "phys",
                            "emoji": "🧸",
                            "tag": "Physical",
                            "title": "Sensory & Motor Play",
                            "desc": "Bubbles, water play, or backyard motor-skills games",
                            "kids": [age],
                        }
                    )
                elif band == "elementary":
                    schedule[day]["Morning"].append(
                        {
                            "time": "9:30 AM - 10:30 AM",
                            "category": "phys",
                            "emoji": "🛝",
                            "tag": "Physical",
                            "title": "Active Playground Play",
                            "desc": "Playground play or tag in the yard",
                            "kids": [age],
                        }
                    )
                elif band in ("tween", "teen"):
                    if "soccer" in hobs:
                        schedule[day]["Morning"].append(
                            {
                                "time": "9:30 AM - 10:30 AM",
                                "category": "phys",
                                "emoji": "⚽",
                                "tag": "Physical",
                                "title": "Soccer Practice",
                                "desc": "Shooting & dribbling drills in yard/park",
                                "kids": [age],
                            }
                        )
                    else:
                        schedule[day]["Morning"].append(
                            {
                                "time": "9:30 AM - 10:30 AM",
                                "category": "phys",
                                "emoji": "🚴",
                                "tag": "Physical",
                                "title": "Outdoor Bike Ride",
                                "desc": "Outdoor bike ride or sports drills",
                                "kids": [age],
                            }
                        )
                elif band == "older_teen":
                    schedule[day]["Morning"].append(
                        {
                            "time": "9:30 AM - 10:30 AM",
                            "category": "phys",
                            "emoji": "🏃",
                            "tag": "Physical",
                            "title": "Morning Workout",
                            "desc": "Morning run or fitness routine",
                            "kids": [age],
                        }
                    )

        if day != field_trip_day:
            for p in profiles:
                age = p["age"]
                needs = p.get("needs", [])
                hobs = p.get("hobbies", [])
                band = get_age_band(age)

                if band == "early_childhood":
                    schedule[day]["Morning"].append(
                        {
                            "time": "10:45 AM - 11:15 AM",
                            "category": "read" if "reading-remediation" in needs else "edu",
                            "emoji": "📖",
                            "tag": "Remediation" if "reading-remediation" in needs else "Educational",
                            "title": "Letter Sounds & Picture Books"
                            if "reading-remediation" in needs
                            else "Story Time & Picture Books",
                            "desc": "Parent-led phonics/letter-sound practice with picture books"
                            if "reading-remediation" in needs
                            else "Parent reads aloud; point-and-name pictures and simple words",
                            "kids": [age],
                        }
                    )
                    schedule[day]["Morning"].append(
                        {
                            "time": "11:15 AM - 11:45 AM",
                            "category": "edu",
                            "emoji": "🔢",
                            "tag": "Math Drills" if "math-drills" in needs else "Educational",
                            "title": "Counting & Shape Practice" if "math-drills" in needs else "Counting & Shape Play",
                            "desc": "Structured counting, sorting, and shape-matching practice"
                            if "math-drills" in needs
                            else "Counting games, shape sorters, and simple pattern play",
                            "kids": [age],
                        }
                    )

                elif band == "elementary":
                    if "reading-remediation" in needs:
                        schedule[day]["Morning"].append(
                            {
                                "time": "10:45 AM - 11:30 AM",
                                "category": "read",
                                "emoji": "📖",
                                "tag": "Remediation",
                                "title": "Guided Reading Practice",
                                "desc": "Phonics cards, sight words & reading log with parent",
                                "kids": [age],
                            }
                        )
                    else:
                        schedule[day]["Morning"].append(
                            {
                                "time": "10:45 AM - 11:30 AM",
                                "category": "edu",
                                "emoji": "📖",
                                "tag": "Educational",
                                "title": "Reading Hour",
                                "desc": "Phonics worksheets & simple storybooks",
                                "kids": [age],
                            }
                        )

                    if "math-drills" in needs:
                        schedule[day]["Morning"].append(
                            {
                                "time": "11:30 AM - 12:00 PM",
                                "category": "edu",
                                "emoji": "🔢",
                                "tag": "Math Drills",
                                "title": "Multiplication Practice",
                                "desc": "Multiplication worksheets & math drills",
                                "kids": [age],
                            }
                        )
                    else:
                        schedule[day]["Morning"].append(
                            {
                                "time": "11:30 AM - 12:00 PM",
                                "category": "edu",
                                "emoji": "🧩",
                                "tag": "Educational",
                                "title": "Math Fun & Games",
                                "desc": "Puzzle cards & counting games",
                                "kids": [age],
                            }
                        )

                elif band == "tween":
                    schedule[day]["Morning"].append(
                        {
                            "time": "10:45 AM - 11:30 AM",
                            "category": "read" if "reading-remediation" in needs else "edu",
                            "emoji": "📖",
                            "tag": "Remediation" if "reading-remediation" in needs else "Educational",
                            "title": "Guided Reading Support" if "reading-remediation" in needs else "Reading Time",
                            "desc": "Targeted reading support & comprehension check-in with parent"
                            if "reading-remediation" in needs
                            else "Independent reading & short book report prep",
                            "kids": [age],
                        }
                    )
                    schedule[day]["Morning"].append(
                        {
                            "time": "11:30 AM - 12:00 PM",
                            "category": "edu",
                            "emoji": "🔢",
                            "tag": "Math Drills" if "math-drills" in needs else "Educational",
                            "title": "Math Practice" if "math-drills" in needs else "Math Fun & Puzzles",
                            "desc": "Targeted drills on tricky concepts (fractions, long division, etc.)"
                            if "math-drills" in needs
                            else "Logic puzzles, brain teasers, or math games",
                            "kids": [age],
                        }
                    )

                elif band == "teen":
                    schedule[day]["Morning"].append(
                        {
                            "time": "10:45 AM - 12:00 PM",
                            "category": "edu",
                            "emoji": "📘",
                            "tag": "Educational",
                            "title": "Core Study Time",
                            "desc": "Summer reading, vocabulary, or algebra prep",
                            "kids": [age],
                        }
                    )

                elif band == "older_teen":
                    if "coding" in hobs:
                        schedule[day]["Morning"].append(
                            {
                                "time": "10:45 AM - 12:00 PM",
                                "category": "edu",
                                "emoji": "💻",
                                "tag": "Coding",
                                "title": "Programming Project",
                                "desc": "Interactive coding courses or python script building",
                                "kids": [age],
                            }
                        )
                    else:
                        schedule[day]["Morning"].append(
                            {
                                "time": "10:45 AM - 12:00 PM",
                                "category": "edu",
                                "emoji": "🔬",
                                "tag": "Educational",
                                "title": "Independent Study",
                                "desc": "Science project, history research, or SAT prep",
                                "kids": [age],
                            }
                        )

        # --- AFTERNOON BLOCK ---
        if day == field_trip_day:
            schedule[day]["Afternoon"].append(
                {
                    "time": "12:00 PM - 3:30 PM",
                    "category": "other",
                    "emoji": "🍔",
                    "tag": "Field Trip",
                    "title": "Outing Lunch & Exploration",
                    "desc": "Picnic or local lunch, then finish exploring the venue (museum galleries, gardens, or pier attractions) before heading home.",
                    "kids": ages,
                }
            )
        elif is_hot:
            if day in ("Tuesday", "Thursday", "Saturday"):
                schedule[day]["Afternoon"].append(
                    {
                        "time": "1:30 PM - 3:30 PM",
                        "category": "phys",
                        "emoji": "🏊",
                        "tag": "Physical",
                        "title": "Belvedere Pool Swim",
                        "desc": "Cool down swim at Belvedere Community Pool",
                        "kids": ages,
                    }
                )
            else:
                schedule[day]["Afternoon"].append(
                    {
                        "time": "1:30 PM - 3:30 PM",
                        "category": "edu",
                        "emoji": "🏛️",
                        "tag": "Educational",
                        "title": "El Sereno Library Visit",
                        "desc": "Quiet reading & book research (AC Environment)",
                        "kids": ages,
                    }
                )
        elif is_rainy:
            schedule[day]["Afternoon"].append(
                {
                    "time": "1:30 PM - 4:00 PM",
                    "category": "edu",
                    "emoji": "🦖",
                    "tag": "Educational",
                    "title": "Museum Outing",
                    "desc": "Science exhibits at California Science Center",
                    "kids": ages,
                }
            )
        else:
            if day in ("Monday", "Wednesday", "Friday"):
                for p in profiles:
                    age = p["age"]
                    hobs = p.get("hobbies", [])
                    band = get_age_band(age)
                    if band == "early_childhood":
                        schedule[day]["Afternoon"].append(
                            {
                                "time": "2:00 PM - 3:00 PM",
                                "category": "edu",
                                "emoji": "🖍️",
                                "tag": "Creative",
                                "title": "Sensory Bin & Simple Crafts",
                                "desc": "Playdough, finger painting, or sticker crafts",
                                "kids": [age],
                                "shuffleable": True,
                            }
                        )
                    elif band == "elementary":
                        schedule[day]["Afternoon"].append(
                            {
                                "time": "2:00 PM - 3:30 PM",
                                "category": "edu",
                                "emoji": "🎨",
                                "tag": "Creative",
                                "title": "Creative Art & Drawing",
                                "desc": "Drawing, painting, and craft worksheets",
                                "kids": [age],
                                "shuffleable": True,
                            }
                        )
                    elif band in ("tween", "teen"):
                        if "music" in hobs:
                            schedule[day]["Afternoon"].append(
                                {
                                    "time": "2:00 PM - 3:30 PM",
                                    "category": "other",
                                    "emoji": "🎸",
                                    "tag": "Music",
                                    "title": "Music Practice",
                                    "desc": "Instrumental rehearsal or listening session",
                                    "kids": [age],
                                    "shuffleable": True,
                                }
                            )
                        else:
                            schedule[day]["Afternoon"].append(
                                {
                                    "time": "2:00 PM - 3:30 PM",
                                    "category": "other",
                                    "emoji": "🛠️",
                                    "tag": "Creative",
                                    "title": "Hobbies & Crafts",
                                    "desc": "Creative building or science model construction",
                                    "kids": [age],
                                    "shuffleable": True,
                                }
                            )
                    elif band == "older_teen":
                        if "volunteering" in hobs:
                            schedule[day]["Afternoon"].append(
                                {
                                    "time": "2:00 PM - 3:30 PM",
                                    "category": "other",
                                    "emoji": "🤝",
                                    "tag": "Volunteering",
                                    "title": "Community Service",
                                    "desc": "Planning/coordinating local volunteer projects",
                                    "kids": [age],
                                    "shuffleable": True,
                                }
                            )
                        else:
                            schedule[day]["Afternoon"].append(
                                {
                                    "time": "2:00 PM - 3:30 PM",
                                    "category": "other",
                                    "emoji": "🎨",
                                    "tag": "Creative",
                                    "title": "Creative Passion Projects",
                                    "desc": "Digital art, writing, or design work",
                                    "kids": [age],
                                    "shuffleable": True,
                                }
                            )
            else:
                schedule[day]["Afternoon"].append(
                    {
                        "time": "2:00 PM - 3:30 PM",
                        "category": "phys",
                        "emoji": "🌳",
                        "tag": "Physical",
                        "title": "El Sereno Rec Center Play",
                        "desc": "Games & sports at the park",
                        "kids": ages,
                        "shuffleable": True,
                    }
                )

        young_ages = [a for a in ages if get_age_band(a) == "early_childhood"]
        independent_reader_ages = [a for a in ages if get_age_band(a) != "early_childhood"]

        if young_ages:
            schedule[day]["Afternoon"].append(
                {
                    "time": "4:00 PM - 5:00 PM",
                    "category": "edu",
                    "emoji": "🤫",
                    "tag": "Educational",
                    "title": "Quiet Time & Picture Books",
                    "desc": "Parent reads picture books aloud; quiet independent play alongside",
                    "kids": young_ages,
                }
            )
        if independent_reader_ages:
            schedule[day]["Afternoon"].append(
                {
                    "time": "4:00 PM - 5:00 PM",
                    "category": "edu",
                    "emoji": "🤫",
                    "tag": "Educational",
                    "title": "Quiet Reading Time",
                    "desc": "Independent reading - chapter books, novels, or hobby reading",
                    "kids": independent_reader_ages,
                }
            )

        # --- EVENING BLOCK ---
        schedule[day]["Evening"].append(
            {
                "time": "6:30 PM - 7:30 PM",
                "category": "phys",
                "emoji": "🚶",
                "tag": "Physical",
                "title": "Evening Stroll",
                "desc": "Neighborhood stroll or backyard active play",
                "kids": ages,
            }
        )

        if day in ("Friday", "Saturday"):
            schedule[day]["Evening"].append(
                {
                    "time": "7:30 PM - 9:00 PM",
                    "category": "other",
                    "emoji": "🍿",
                    "tag": "Leisure",
                    "title": "Family Night",
                    "desc": "Movie night or board games together",
                    "kids": ages,
                }
            )
        else:
            early_bedtime_ages = [a for a in ages if get_age_band(a) in ("early_childhood", "elementary")]
            older_kid_ages = [a for a in ages if get_age_band(a) in ("tween", "teen", "older_teen")]

            if early_bedtime_ages:
                schedule[day]["Evening"].append(
                    {
                        "time": "7:30 PM - 8:30 PM",
                        "category": "other",
                        "emoji": "🌙",
                        "tag": "Leisure",
                        "title": "Wind-down Reading",
                        "desc": "Phonics story reading & early bedtime",
                        "kids": early_bedtime_ages,
                    }
                )
            if older_kid_ages:
                schedule[day]["Evening"].append(
                    {
                        "time": "7:30 PM - 9:00 PM",
                        "category": "other",
                        "emoji": "🛋️",
                        "tag": "Leisure",
                        "title": "Tween/Teen Relaxation",
                        "desc": "Personal reading, project prep, next day planning",
                        "kids": older_kid_ages,
                    }
                )

    return schedule
