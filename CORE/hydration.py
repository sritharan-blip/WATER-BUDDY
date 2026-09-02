import re
from datetime import date, timedelta

DRINK_TYPES = [
    "water",
    "sparkling water",
    "tea",
    "coffee",
    "juice",
    "milk",
    "smoothie",
    "sports drink",
    "electrolyte drink",
    "protein shake",
    "coconut water",
    "other",
]

QUICK_ADD_PRESETS = [50, 100, 150, 200, 250, 330, 500, 750, 1000]

UNIT_LABELS = {
    "ml": "ml",
    "l": "L",
    "oz": "oz",
    "cup": "cups",
}

UNIT_CONVERSIONS = {
    "ml": 1,
    "l": 1000,
    "oz": 29.5735,
    "cup": 240,
}

ACTIVITY_FACTORS = {
    "low": 0.08,
    "moderate": 0.15,
    "high": 0.22,
    "very_high": 0.30,
}

CLIMATE_FACTORS = {
    "cool": 0.03,
    "warm": 0.10,
    "hot": 0.18,
}

TITLE_TIERS = {
    1: "Thirsty Newbie",
    2: "Sip Starter",
    3: "Steady Sipper",
    4: "Hydro Enthusiast",
    5: "Flow Finder",
    6: "Aqua Adept",
    7: "Hydration Hero",
    8: "Water Warden",
    9: "Ripple Ruler",
    10: "Tide Master",
    11: "Ocean Oracle",
    12: "Hydration Legend",
}

# Comprehensive Age-Based Recommendations
AGE_INTAKE_RECOMMENDATIONS = [
    {
        "age_range": (0, 8),
        "min": 0,
        "max": 12,
        "recommended_ml": 1200,
        "cups_per_day": 5,
        "note": "Young children need frequent hydration. Encourage water after playtime.",
        "hydration_tips": "Make hydration fun with colorful water bottles and water-based games.",
    },
    {
        "age_range": (9, 13),
        "min": 9,
        "max": 13,
        "recommended_ml": 1800,
        "cups_per_day": 7,
        "note": "Pre-teens should drink water before, during, and after physical activity.",
        "hydration_tips": "Start establishing healthy hydration habits. Drink before feeling thirsty.",
    },
    {
        "age_range": (14, 18),
        "min": 14,
        "max": 18,
        "recommended_ml": 2600,
        "cups_per_day": 10,
        "note": "Teenagers are active and need consistent hydration support.",
        "hydration_tips": "Keep a water bottle handy during school and sports.",
    },
    {
        "age_range": (19, 30),
        "min": 19,
        "max": 30,
        "recommended_ml": 3000,
        "cups_per_day": 12,
        "note": "Young adults benefit from 3L daily intake with exercise.",
        "hydration_tips": "Set reminders on your phone or use an app to track hydration.",
    },
    {
        "age_range": (31, 50),
        "min": 31,
        "max": 50,
        "recommended_ml": 3200,
        "cups_per_day": 13,
        "note": "Middle-aged adults: maintain consistent hydration to support metabolism.",
        "hydration_tips": "Drink a glass of water with each meal and snack.",
    },
    {
        "age_range": (51, 65),
        "min": 51,
        "max": 65,
        "recommended_ml": 2800,
        "cups_per_day": 11,
        "note": "Adjust hydration based on activity level; thirst cues may decline.",
        "hydration_tips": "Don't wait until you're thirsty. Establish a regular drinking schedule.",
    },
    {
        "age_range": (66, 100),
        "min": 66,
        "max": 100,
        "recommended_ml": 2600,
        "cups_per_day": 10,
        "note": "Seniors: consistent hydration is crucial for kidney and heart function.",
        "hydration_tips": "Set hourly reminders and choose water, herbal tea, and water-rich foods.",
    },
]

# Occupation-Based Recommendations
OCCUPATION_RECOMMENDATIONS = {
    "Student": {
        "recommended_ml": 2800,
        "extra_factor": 0.1,
        "note": "Students should drink more during study sessions and exams.",
        "tips": "Keep water nearby during classes and study breaks.",
        "icon": "📚",
    },
    "Office Worker": {
        "recommended_ml": 2600,
        "extra_factor": 0.08,
        "note": "Office workers: stay hydrated to boost focus and reduce fatigue.",
        "tips": "Fill a water bottle each morning and refill at lunch.",
        "icon": "💼",
    },
    "Athlete": {
        "recommended_ml": 4000,
        "extra_factor": 0.35,
        "note": "Athletes need 4-6L daily depending on intensity and climate.",
        "tips": "Drink 500ml 2-3 hours before exercise, then 200ml every 15-20 mins.",
        "icon": "⚽",
    },
    "Construction Worker": {
        "recommended_ml": 4500,
        "extra_factor": 0.40,
        "note": "Physical workers lose more fluids; prioritize hydration.",
        "tips": "Drink electrolyte drinks and water mix throughout the day.",
        "icon": "🏗️",
    },
    "Healthcare Worker": {
        "recommended_ml": 3500,
        "extra_factor": 0.20,
        "note": "Long shifts and high stress increase hydration needs.",
        "tips": "Start each shift with full hydration and drink regularly.",
        "icon": "🏥",
    },
    "Teacher": {
        "recommended_ml": 3000,
        "extra_factor": 0.12,
        "note": "Teachers talk often; maintain hydration for voice and energy.",
        "tips": "Keep water at your desk and drink during class transitions.",
        "icon": "🍎",
    },
    "Driver": {
        "recommended_ml": 2800,
        "extra_factor": 0.10,
        "note": "Long driving periods can cause dehydration; stay alert.",
        "tips": "Drink water at every stop. Avoid excessive caffeine.",
        "icon": "🚗",
    },
    "Chef": {
        "recommended_ml": 3800,
        "extra_factor": 0.25,
        "note": "Hot kitchens cause significant fluid loss.",
        "tips": "Drink water regularly; keep bottle at cooking stations.",
        "icon": "👨‍🍳",
    },
    "Fitness Trainer": {
        "recommended_ml": 4200,
        "extra_factor": 0.38,
        "note": "Active role requires high hydration levels.",
        "tips": "Drink before, during, and after client sessions.",
        "icon": "💪",
    },
    "Software Developer": {
        "recommended_ml": 2600,
        "extra_factor": 0.08,
        "note": "Long coding sessions: maintain hydration for mental focus.",
        "tips": "Set hourly water breaks; keep water bottle at desk.",
        "icon": "💻",
    },
    "Nurse": {
        "recommended_ml": 3600,
        "extra_factor": 0.22,
        "note": "Fast-paced shifts and standing time increase hydration needs.",
        "tips": "Drink at shift start, during breaks, and before going home.",
        "icon": "🏥",
    },
    "Sales Representative": {
        "recommended_ml": 3000,
        "extra_factor": 0.15,
        "note": "Travel and meetings: maintain energy and mental clarity.",
        "tips": "Keep water bottle during meetings and travel.",
        "icon": "📊",
    },
    "Home-based": {
        "recommended_ml": 2600,
        "extra_factor": 0.05,
        "note": "Flexible schedule allows for consistent hydration.",
        "tips": "Set reminders to drink water with meals and snacks.",
        "icon": "🏠",
    },
    "Retired": {
        "recommended_ml": 2400,
        "extra_factor": 0.05,
        "note": "Stay hydrated for overall health and vitality.",
        "tips": "Establish regular drinking times throughout the day.",
        "icon": "🌴",
    },
}


def calculate_hydration_goal(age, weight, activity_level, climate, occupation=None):
    base = weight * 35
    if age < 18:
        base *= 0.9
    activity = ACTIVITY_FACTORS.get(activity_level, 0.15)
    climate_adj = CLIMATE_FACTORS.get(climate, 0.05)
    goal = base * (1 + activity + climate_adj)
    
    # Apply occupation modifier if provided
    if occupation and occupation in OCCUPATION_RECOMMENDATIONS:
        occ_data = OCCUPATION_RECOMMENDATIONS[occupation]
        # Blend calculated goal with occupation recommendation
        occ_goal = occ_data["recommended_ml"]
        goal = (goal + occ_goal) / 2
    
    return max(int(round(goal)), 1800)


def get_age_recommendation(age):
    """Get detailed age-based hydration recommendation."""
    for rec in AGE_INTAKE_RECOMMENDATIONS:
        if rec["age_range"][0] <= age <= rec["age_range"][1]:
            return {
                "age_range": f"{rec['age_range'][0]}–{rec['age_range'][1]}",
                "recommended_ml": rec["recommended_ml"],
                "cups_per_day": rec["cups_per_day"],
                "note": rec["note"],
                "hydration_tips": rec["hydration_tips"],
            }
    return {
        "age_range": "18–30",
        "recommended_ml": 3000,
        "cups_per_day": 12,
        "note": "Standard adult hydration target.",
        "hydration_tips": "Drink consistently throughout the day.",
    }


def get_occupation_recommendation(occupation):
    """Get occupation-based hydration recommendation."""
    if occupation in OCCUPATION_RECOMMENDATIONS:
        rec = OCCUPATION_RECOMMENDATIONS[occupation]
        return {
            "occupation": occupation,
            "recommended_ml": rec["recommended_ml"],
            "extra_factor": rec["extra_factor"],
            "note": rec["note"],
            "tips": rec["tips"],
            "icon": rec["icon"],
        }
    return {
        "occupation": "General",
        "recommended_ml": 2600,
        "extra_factor": 0.0,
        "note": "Standard hydration for most occupations.",
        "tips": "Establish a regular drinking schedule.",
        "icon": "💼",
    }


def get_climate_recommendation(climate):
    """Get a climate-based hydration recommendation."""
    climate_data = {
        "cool": {
            "recommended_ml": 2500,
            "note": "Cool weather usually means less fluid loss, but regular hydration still matters.",
            "tips": "Keep sipping throughout the day, even when you do not feel thirsty.",
        },
        "warm": {
            "recommended_ml": 2700,
            "note": "Warm weather increases fluid needs through light sweating and heat exposure.",
            "tips": "Add extra water around outdoor time and physical activity.",
        },
        "hot": {
            "recommended_ml": 3000,
            "note": "Hot weather increases fluid loss, so a higher daily intake is helpful.",
            "tips": "Drink regularly and consider electrolytes during prolonged sweating.",
        },
    }
    recommendation = climate_data.get(climate, climate_data["warm"])
    return {
        "climate": climate,
        "recommended_ml": recommendation["recommended_ml"],
        "note": recommendation["note"],
        "tips": recommendation["tips"],
    }


def get_all_occupations():
    """Return list of all occupation options."""
    return sorted(list(OCCUPATION_RECOMMENDATIONS.keys()))


def convert_volume_to_ml(amount, unit="ml"):
    if unit not in UNIT_CONVERSIONS:
        return amount
    return int(round(amount * UNIT_CONVERSIONS[unit]))


def get_progress_percent(goal_ml, intake_ml):
    if goal_ml <= 0:
        return 0
    return min(100, int((intake_ml / goal_ml) * 100))


def calculate_streak(entries):
    if not entries:
        return 0
    streak = 0
    current = date.today()
    while True:
        key = current.strftime("%Y-%m-%d")
        if any(entry.get("date") == key for entry in entries):
            streak += 1
            current -= timedelta(days=1)
        else:
            break
    return streak


def get_level_info(points):
    level = 1
    xp_remaining = points
    xp_needed = 50
    while xp_remaining >= xp_needed:
        xp_remaining -= xp_needed
        level += 1
        xp_needed = 50 + (level - 1) * 15
    title = TITLE_TIERS.get(level, "Hydration Deity")
    progress_pct = int((xp_remaining / xp_needed) * 100) if xp_needed else 0
    return {
        "level": level,
        "title": title,
        "xp_into_level": xp_remaining,
        "xp_needed": xp_needed,
        "xp_progress_pct": progress_pct,
    }


def calculate_hydration_iq(goal_ml, intake_ml, streak_days):
    if goal_ml <= 0:
        return 0
    score = min(100, int(intake_ml / goal_ml * 70 + min(streak_days, 30) * 1.0 + 10))
    return max(0, score)


def get_motivation(progress_pct):
    if progress_pct >= 100:
        return "🎉 You've hit your goal — keep the momentum."
    if progress_pct >= 75:
        return "🚀 Great progress! One more push for the goal."
    if progress_pct >= 40:
        return "💧 Nice pace — small sips add up fast." 
    return "🌱 Start with a gentle glass and build your rhythm."


def parse_drink_text(text):
    text = text.lower()
    amount = None
    unit = "ml"
    drink = "water"
    numbers = re.findall(r"(\d+(?:\.\d+)?)", text)
    if numbers:
        amount = float(numbers[0])
    for key in DRINK_TYPES:
        if key in text:
            drink = key
            break
    for suffix in ["ml", "milliliters", "milliliter"]:
        if suffix in text:
            unit = "ml"
    if "l" in text and "ml" not in text:
        unit = "l"
    if "oz" in text or "ounce" in text:
        unit = "oz"
    if "cup" in text:
        unit = "cup"
    if amount is None:
        return None
    return {
        "amount_ml": convert_volume_to_ml(amount, unit),
        "drink": drink,
        "raw_text": text,
    }
