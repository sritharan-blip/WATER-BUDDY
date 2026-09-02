import json
from pathlib import Path
from datetime import date
from core.hydration import calculate_hydration_goal, calculate_streak

# Create data directory in user's home folder (avoid system32 permission issues)
APP_DATA_DIR = Path.home() / ".water_buddy"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = APP_DATA_DIR / "water_buddy_data.json"
SCHEMA_VERSION = 1

DEFAULT_CONTAINERS = [
    {
        "name": "Classic Bottle",
        "capacity_ml": 500,
        "material": "glass",
        "color": "teal",
        "icon": "🥤",
        "usage_count": 0,
        "is_full": True,
    },
    {
        "name": "Sport Flask",
        "capacity_ml": 750,
        "material": "plastic",
        "color": "blue",
        "icon": "🚰",
        "usage_count": 0,
        "is_full": True,
    },
    {
        "name": "Hydro Jug",
        "capacity_ml": 1000,
        "material": "steel",
        "color": "silver",
        "icon": "🧴",
        "usage_count": 0,
        "is_full": True,
    },
]

DEFAULT_DATA = {
    "schema_version": SCHEMA_VERSION,
    "profile": {
        "name": "",
        "age": 25,
        "weight": 70,
        "activity": "moderate",
        "climate": "warm",
        "occupation": "Student",
        "goal": calculate_hydration_goal(25, 70, "moderate", "warm", "Student"),
        "custom_goal": None,
        "anonymous_mode": False,
        "onboarding_complete": False,
        "custom_drink_types": [],
    },
    "settings": {
        "theme": "ocean",
        "notifications": True,
        "auto_save": True,
        "hide_tips": False,
    },
    "buddy": {
        "species": "duckling",
        "eyes": "sparkle",
        "mouth": "smile",
        "accessories": [],
        "environment": "ocean",
        "mood": "happy",
        "name": "Buddy",
        "custom_emoji": "",
    },
    "entries": [],
    "stats": {
        "points": 0,
        "streak": 0,
        "coins": 0,
        "achievements": [],
    },
    "shop": {
        "owned": ["default"],
        "selected": "default",
    },
    "quests_claimed": [],
    "containers": DEFAULT_CONTAINERS.copy(),
    "quick_add": [50, 100, 150, 200, 250, 330, 500, 750, 1000],
}


def _ensure_defaults(data):
    if not isinstance(data, dict):
        data = {}
    profile = data.setdefault("profile", {})
    profile.setdefault("name", "")
    profile.setdefault("age", 25)
    profile.setdefault("weight", 70)
    profile.setdefault("activity", "moderate")
    profile.setdefault("climate", "warm")
    profile.setdefault("occupation", "Student")
    profile.setdefault("custom_goal", None)
    if profile.get("custom_goal") is None:
        profile["goal"] = calculate_hydration_goal(
            profile.get("age", 25),
            profile.get("weight", 70),
            profile.get("activity", "moderate"),
            profile.get("climate", "warm"),
            profile.get("occupation", "Student"),
        )
    profile.setdefault("anonymous_mode", False)
    profile.setdefault("onboarding_complete", False)
    profile.setdefault("custom_drink_types", [])

    data.setdefault("entries", [])
    stats = data.setdefault("stats", {})
    stats.setdefault("points", sum(entry.get("amount", 0) // 100 for entry in data["entries"]))
    stats.setdefault("streak", calculate_streak(data["entries"]))
    stats.setdefault("coins", 0)
    stats.setdefault("achievements", [])
    data.setdefault("settings", {
        "theme": "ocean",
        "notifications": True,
        "auto_save": True,
        "hide_tips": False,
    })
    data.setdefault("buddy", {
        "species": "duckling",
        "eyes": "sparkle",
        "mouth": "smile",
        "accessories": [],
        "environment": "ocean",
        "mood": "happy",
        "name": "Buddy",
        "custom_emoji": "",
    })
    data.setdefault("shop", {"owned": ["default"], "selected": "default"})
    data.setdefault("quests_claimed", [])
    data.setdefault("containers", DEFAULT_CONTAINERS.copy())
    data.setdefault("quick_add", DEFAULT_DATA["quick_add"].copy())
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def _migrate_data(data):
    version = data.get("schema_version", 0)
    if version < 1:
        data["profile"] = data.get("profile", {})
        data["profile"].setdefault("custom_drink_types", [])
        data["stats"] = data.get("stats", {})
        data["stats"].setdefault("achievements", [])
        data["schema_version"] = 1
    return _ensure_defaults(data)


def load_data():
    try:
        if not DATA_FILE.exists():
            save_data(DEFAULT_DATA)
            return _ensure_defaults(DEFAULT_DATA.copy())
        with DATA_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            data = {}
        data = _migrate_data(data)
    except Exception:
        data = _ensure_defaults(DEFAULT_DATA.copy())
    return data


def save_data(data):
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with DATA_FILE.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
    except Exception:
        pass
