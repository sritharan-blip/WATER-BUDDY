from datetime import date
from core.hydration import get_progress_percent, get_level_info

ACHIEVEMENT_DEFINITIONS = [
    {
        "id": "first_sip",
        "name": "First Sip",
        "emoji": "💧",
        "desc": "Log your very first drink.",
        "category": "🌱 Beginner",
        "rarity": "COMMON",
        "xp": 25,
        "check": lambda data: len(data.get("entries", [])) >= 1,
    },
    {
        "id": "century_club",
        "name": "Century Club",
        "emoji": "💯",
        "desc": "Log 100 drinks total.",
        "category": "🎯 Consistency",
        "rarity": "RARE",
        "xp": 150,
        "check": lambda data: len(data.get("entries", [])) >= 100,
    },
    {
        "id": "week_streak",
        "name": "Hydration Hero",
        "emoji": "🔥",
        "desc": "Hit a 7-day streak.",
        "category": "🔥 Streak",
        "rarity": "RARE",
        "xp": 120,
        "check": lambda data: data.get("stats", {}).get("streak", 0) >= 7,
    },
    {
        "id": "goal_crusher",
        "name": "Goal Crusher",
        "emoji": "🏆",
        "desc": "Hit your daily goal.",
        "category": "💧 Volume",
        "rarity": "EPIC",
        "xp": 200,
        "check": lambda data: get_progress_percent(
            data.get("profile", {}).get("goal", 2600),
            sum(entry.get("amount", 0) for entry in data.get("entries", []) if entry.get("date") == date.today().strftime("%Y-%m-%d"))
        ) >= 100,
    },
    {
        "id": "variety",
        "name": "Mix It Up",
        "emoji": "🍹",
        "desc": "Log 3 different drink types.",
        "category": "🎯 Consistency",
        "rarity": "COMMON",
        "xp": 40,
        "check": lambda data: len({entry.get("drink", "water") for entry in data.get("entries", [])}) >= 3,
    },
    {
        "id": "level_5",
        "name": "Rising Star",
        "emoji": "⭐",
        "desc": "Reach Level 5.",
        "category": "🎮 Challenges",
        "rarity": "EPIC",
        "xp": 180,
        "check": lambda data: get_level_info(data.get("stats", {}).get("points", 0))["level"] >= 5,
    },
    {
        "id": "early_bird",
        "name": "Early Bird",
        "emoji": "🌅",
        "desc": "Log a drink before 8 AM.",
        "category": "🐣 Buddy",
        "rarity": "RARE",
        "xp": 80,
        "check": lambda data: any(entry.get("time", "12:00") < "08:00" for entry in data.get("entries", [])),
    },
    {
        "id": "night_owl",
        "name": "Night Owl",
        "emoji": "🌙",
        "desc": "Log a drink after 10 PM.",
        "category": "🌙 Challenges",
        "rarity": "COMMON",
        "xp": 50,
        "check": lambda data: any(entry.get("time", "00:00") > "22:00" for entry in data.get("entries", [])),
    },
    {
        "id": "hydration_master",
        "name": "Hydration Master",
        "emoji": "🧠",
        "desc": "Log 30 days of hydration.",
        "category": "🏅 Consistency",
        "rarity": "LEGENDARY",
        "xp": 300,
        "check": lambda data: len({entry.get("date") for entry in data.get("entries", [])}) >= 30,
    },
    {
        "id": "goal_smasher",
        "name": "Goal Smasher",
        "emoji": "💥",
        "desc": "Surpass your daily goal by 150%.",
        "category": "🔥 Volume",
        "rarity": "EPIC",
        "xp": 220,
        "check": lambda data: any(
            get_progress_percent(
                data.get("profile", {}).get("goal", 2600),
                sum(entry.get("amount", 0) for entry in data.get("entries", []) if entry.get("date") == target_date)
            ) >= 150
            for target_date in {entry.get("date") for entry in data.get("entries", []) if entry.get("date")}
        ),
    },
]


def evaluate_achievements(data):
    if data is None:
        return []
    unlocked = set(data.get("stats", {}).get("achievements", []))
    newly_unlocked = []
    for achievement in ACHIEVEMENT_DEFINITIONS:
        if achievement["id"] not in unlocked and achievement["check"](data):
            unlocked.add(achievement["id"])
            newly_unlocked.append(achievement)
    data.setdefault("stats", {})["achievements"] = list(unlocked)
    return newly_unlocked
