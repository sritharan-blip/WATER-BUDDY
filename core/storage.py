import json
import hashlib
import hmac
import re
import secrets
from pathlib import Path
from datetime import date
from core.hydration import calculate_hydration_goal, calculate_streak

# Create data directory in user's home folder (avoid system32 permission issues)
APP_DATA_DIR = Path.home() / ".water_buddy"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = APP_DATA_DIR / "water_buddy_data.json"
ACCOUNTS_FILE = APP_DATA_DIR / "water_buddy_accounts.json"
REMEMBERED_LOGIN_FILE = APP_DATA_DIR / "water_buddy_remembered_login.json"
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
        "gender": "Prefer not to say",
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
        "reminder_interval_minutes": 60,
        "reminder_amount_ml": 250,
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
        "equipped": [],
        "skin": "classic",
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
    profile.setdefault("gender", "Prefer not to say")
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
        "reminder_interval_minutes": 60,
        "reminder_amount_ml": 250,
    })
    data["settings"].setdefault("reminder_interval_minutes", 60)
    data["settings"].setdefault("reminder_amount_ml", 250)
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
    data.setdefault("shop", {"owned": ["default"], "selected": "default", "equipped": [], "skin": "classic"})
    data["shop"].setdefault("owned", ["default"])
    data["shop"].setdefault("equipped", [])
    data["shop"].setdefault("skin", "classic")
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


def _user_data_file(username="default"):
    safe_username = re.sub(r"[^a-zA-Z0-9_-]", "_", username.strip().lower()) or "default"
    return APP_DATA_DIR / f"water_buddy_{safe_username}.json"


def load_accounts():
    try:
        if ACCOUNTS_FILE.exists():
            with ACCOUNTS_FILE.open("r", encoding="utf-8") as handle:
                accounts = json.load(handle)
            return accounts if isinstance(accounts, dict) else {}
    except Exception:
        pass
    return {}


def save_accounts(accounts):
    try:
        with ACCOUNTS_FILE.open("w", encoding="utf-8") as handle:
            json.dump(accounts, handle, indent=2)
    except Exception:
        pass


def create_account(username, password):
    username = username.strip().lower()
    accounts = load_accounts()
    if username in accounts:
        return False
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    accounts[username] = {"salt": salt, "password_hash": password_hash}
    save_accounts(accounts)
    save_data(_ensure_defaults(DEFAULT_DATA.copy()), username)
    return True


def verify_account(username, password):
    account = load_accounts().get(username.strip().lower())
    if not account:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), account["salt"].encode(), 120000
    ).hex()
    return hmac.compare_digest(candidate, account.get("password_hash", ""))


def account_exists(username):
    return username.strip().lower() in load_accounts()


def remember_login(username):
    """Remember the local app's last username without storing a password."""
    try:
        with REMEMBERED_LOGIN_FILE.open("w", encoding="utf-8") as handle:
            json.dump({"username": username.strip().lower()}, handle)
    except Exception:
        pass


def load_remembered_login():
    try:
        with REMEMBERED_LOGIN_FILE.open("r", encoding="utf-8") as handle:
            remembered = json.load(handle)
        username = remembered.get("username", "") if isinstance(remembered, dict) else ""
        return username.strip().lower() or None
    except Exception:
        return None


def forget_login():
    """Clear browser/session state at logout. No shared server-side login cache is used."""
    try:
        REMEMBERED_LOGIN_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def load_data(username="default"):
    data_file = _user_data_file(username)
    try:
        if not data_file.exists():
            save_data(DEFAULT_DATA, username)
            return _ensure_defaults(DEFAULT_DATA.copy())
        with data_file.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            data = {}
        data = _migrate_data(data)
    except Exception:
        data = _ensure_defaults(DEFAULT_DATA.copy())
    return data


def save_data(data, username="default"):
    try:
        safe_data = _ensure_defaults(data if isinstance(data, dict) else {})
        data_file = _user_data_file(username)
        data_file.parent.mkdir(parents=True, exist_ok=True)
        with data_file.open("w", encoding="utf-8") as handle:
            json.dump(safe_data, handle, indent=2)
    except Exception:
        pass
