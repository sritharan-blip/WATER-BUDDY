import copy
import hashlib
import hmac
import json
import os
import secrets
import sys
import tempfile
import types
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Make the repo root importable when Streamlit runs the app from a nested MAIN folder
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent if APP_DIR.name.lower() == "main" else APP_DIR

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Support upper/lowercase folder names on Linux-hosted deploys
for folder_name in ["core", "CORE", "services", "SERVICES"]:
    candidate = REPO_ROOT / folder_name
    if candidate.is_dir():
        package_name = folder_name.lower()
        if package_name not in sys.modules:
            module = types.ModuleType(package_name)
            module.__path__ = [str(candidate)]
            sys.modules[package_name] = module

from core.analytics import get_monthly_calendar, get_weekly_totals
from core.achievements import ACHIEVEMENT_DEFINITIONS, evaluate_achievements
from core.hydration import (
    DRINK_TYPES,
    calculate_hydration_goal,
    calculate_streak,
    get_level_info,
    get_progress_percent,
    get_motivation,
    get_age_recommendation,
    get_occupation_recommendation,
    get_climate_recommendation,
    get_all_occupations,
    parse_drink_text,
)
from core.insights import generate_insights
from core import storage as storage


def _fallback_create_account(username, password):
    account_file = Path.home() / ".water_buddy" / "water_buddy_accounts.json"
    try:
        accounts = {}
        if account_file.exists():
            with account_file.open("r", encoding="utf-8") as handle:
                accounts = json.load(handle)
        username = username.strip().lower()
        if username in accounts:
            return False
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 120000
        ).hex()
        accounts[username] = {"salt": salt, "password_hash": password_hash}
        account_file.parent.mkdir(parents=True, exist_ok=True)
        with account_file.open("w", encoding="utf-8") as handle:
            json.dump(accounts, handle, indent=2)
        storage.save_data(storage.DEFAULT_DATA, username)
        return True
    except Exception:
        return False


def _fallback_verify_account(username, password):
    account_file = Path.home() / ".water_buddy" / "water_buddy_accounts.json"
    try:
        with account_file.open("r", encoding="utf-8") as handle:
            account = json.load(handle).get(username.strip().lower())
        if not account:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), account["salt"].encode(), 120000
        ).hex()
        return hmac.compare_digest(candidate, account.get("password_hash", ""))
    except Exception:
        return False


DEFAULT_DATA = storage.DEFAULT_DATA
create_account = getattr(storage, "create_account", _fallback_create_account)
forget_login = getattr(storage, "forget_login", lambda: None)
load_data = storage.load_data
load_remembered_login = getattr(storage, "load_remembered_login", lambda: None)
remember_login = getattr(storage, "remember_login", lambda username: None)
save_data = storage.save_data
verify_account = getattr(storage, "verify_account", _fallback_verify_account)
account_exists = getattr(storage, "account_exists", lambda username: False)
from services.ai_provider import get_coach
from services.vision_provider import get_vision_analyzer

APP_TITLE = "💧 Water Buddy — Hydration Quest"

THEMES = {
    "ocean": {
        "background": "linear-gradient(180deg, #03131f 0%, #061a2a 45%, #061822 100%)",
        "surface": "rgba(255,255,255,0.08)",
        "surface_alt": "rgba(255,255,255,0.05)",
        "border": "rgba(255,255,255,0.16)",
        "accent": "#38d1f6",
        "accent_soft": "rgba(56,209,246,0.18)",
        "text": "#e8f9ff",
        "muted": "#95b8cc",
        "shadow": "0 32px 120px rgba(0, 120, 210, 0.12)",
        "mascot": "🐬",
        "mascot_name": "Dolphin",
    },
    "midnight": {
        "background": "linear-gradient(180deg, #02050b 0%, #091624 50%, #07101b 100%)",
        "surface": "rgba(255,255,255,0.06)",
        "surface_alt": "rgba(255,255,255,0.04)",
        "border": "rgba(255,255,255,0.12)",
        "accent": "#7c5dff",
        "accent_soft": "rgba(124,93,255,0.18)",
        "text": "#f3f6ff",
        "muted": "#9aa8c2",
        "shadow": "0 32px 120px rgba(62, 73, 141, 0.16)",
        "mascot": "🦉",
        "mascot_name": "Moon Owl",
    },
    "forest": {
        "background": "linear-gradient(180deg, #081509 0%, #11271b 40%, #0b160f 100%)",
        "surface": "rgba(255,255,255,0.07)",
        "surface_alt": "rgba(255,255,255,0.04)",
        "border": "rgba(255,255,255,0.14)",
        "accent": "#3cd695",
        "accent_soft": "rgba(60,214,149,0.18)",
        "text": "#ecfbf3",
        "muted": "#98b9a1",
        "shadow": "0 32px 120px rgba(0, 120, 76, 0.12)",
        "mascot": "🦊",
        "mascot_name": "Forest Fox",
    },
    "cyber": {
        "background": "linear-gradient(180deg, #04040a 0%, #091022 40%, #0b111d 100%)",
        "surface": "rgba(255,255,255,0.06)",
        "surface_alt": "rgba(255,255,255,0.03)",
        "border": "rgba(255,255,255,0.12)",
        "accent": "#6af5ff",
        "accent_soft": "rgba(106,245,255,0.16)",
        "text": "#e6f7ff",
        "muted": "#99b1c4",
        "shadow": "0 32px 120px rgba(39, 220, 255, 0.12)",
        "mascot": "🤖",
        "mascot_name": "Hydro Bot",
    },
    "sunset": {
        "background": "linear-gradient(180deg, #140d24 0%, #2a143f 40%, #1a1f35 100%)",
        "surface": "rgba(255,255,255,0.08)",
        "surface_alt": "rgba(255,255,255,0.05)",
        "border": "rgba(255,255,255,0.14)",
        "accent": "#ff9d5c",
        "accent_soft": "rgba(255,157,92,0.18)",
        "text": "#f8f1f8",
        "muted": "#bba5b8",
        "shadow": "0 32px 120px rgba(255, 135, 75, 0.12)",
        "mascot": "🦅",
        "mascot_name": "Sunset Phoenix",
    },
    "day": {
        "background": "linear-gradient(180deg, #eaf6ff 0%, #c9e8ff 45%, #b8dcf4 100%)",
        "surface": "rgba(255,255,255,0.94)",
        "surface_alt": "rgba(255,255,255,0.88)",
        "border": "rgba(5,57,94,0.12)",
        "accent": "#2276d2",
        "accent_soft": "rgba(34,118,210,0.16)",
        "text": "#0d1f38",
        "muted": "#4b6f8a",
        "shadow": "0 32px 120px rgba(0, 0, 0, 0.08)",
        "mascot": "🐰",
        "mascot_name": "Day Bunny",
    },
}

NAV_ITEMS = [
    {"id": "Home", "label": "Home", "icon": "🏠"},
    {"id": "Hydrate", "label": "Hydrate", "icon": "💧"},
    {"id": "Verify", "label": "Verify", "icon": "📸"},
    {"id": "Buddy", "label": "Buddy", "icon": "🐣"},
    {"id": "Quests", "label": "Quests", "icon": "🎯"},
    {"id": "Achievements", "label": "Achievements", "icon": "🏆"},
    {"id": "Analytics", "label": "Analytics", "icon": "📊"},
    {"id": "Insights", "label": "Insights", "icon": "🧠"},
    {"id": "Calendar", "label": "Calendar", "icon": "📅"},
    {"id": "Reminders", "label": "Reminders", "icon": "⏰"},
    {"id": "Settings", "label": "Settings", "icon": "⚙️"},
]

HYDRATION_TIPS = [
    "Keep a refillable bottle where you can see it so sipping becomes automatic.",
    "Drink steadily through the day instead of trying to catch up all at once.",
    "Pair water with routines you already do, like meals, study breaks, or commuting.",
    "After exercise or time in heat, replace fluids gradually and listen to your body.",
    "Drink a glass of water when you wake up to restart your daily rhythm.",
    "Add lemon, mint, cucumber, or berries when plain water feels boring.",
    "Take a few sips before each meal and snack.",
    "Keep a bottle beside your workspace so it stays within easy reach.",
    "Use a marked bottle to make your progress visible throughout the day.",
    "Drink extra water during hot, humid, or very dry weather.",
    "Sip during travel instead of waiting until you feel thirsty.",
    "Pair your afternoon coffee with a glass of water.",
    "Drink before, during, and after a workout to support steady hydration.",
    "Set a gentle reminder for regular sips instead of one large catch-up drink.",
    "Choose water with meals when you want a simple hydration boost.",
    "Refill your bottle as soon as it is empty so the next drink is ready.",
    "Keep a spare bottle in your bag for busy days away from home.",
    "A cool drink can make it easier to sip more often in warm weather.",
    "Notice your urine color as one everyday clue about hydration, not a diagnosis.",
    "Drink a little more when you are sweating or spending time outdoors.",
    "Make your first study or work break a water break.",
    "Use a reusable straw if it helps you drink more comfortably.",
    "Take water with you when you run errands so convenience works in your favor.",
    "Spread drinks across the day to keep your energy routine steady.",
    "Give your bottle a quick wash when you refill it for a fresh start.",
    "Try sparkling water when you want variety without a sugary drink.",
    "Drink with your evening meal, then keep a small amount nearby if you need it.",
    "Listen to thirst, especially when your routine or environment changes.",
    "Celebrate consistency: small sips repeated often add up.",
    "Make hydration part of a routine you already enjoy, like a walk or playlist.",
]

QUESTS = [
    {
        "id": "daily_goal",
        "title": "Reach Today’s Goal",
        "subtitle": "Drink 100% of your daily target.",
        "reward": {"xp": 100, "coins": 20},
        "category": "TODAY",
    },
    {
        "id": "weekly_streak",
        "title": "Maintain the Streak",
        "subtitle": "Keep your streak going for 7 days.",
        "reward": {"xp": 250, "coins": 40},
        "category": "WEEKLY",
    },
    {
        "id": "verify_bottles",
        "title": "Verification Run",
        "subtitle": "Analyze 5 containers",
        "reward": {"xp": 180, "coins": 30},
        "category": "SPECIAL",
    },
]

REWARD_ITEMS = [
    {"id": "cooling_glasses", "name": "Cooling Glasses", "cost": 35, "category": "Wearable", "rarity": "COMMON"},
    {"id": "beach_shirt", "name": "Beach Shirt", "cost": 50, "category": "Wearable", "rarity": "COMMON"},
    {"id": "beanie", "name": "Cozy Beanie", "cost": 65, "category": "Wearable", "rarity": "COMMON"},
    {"id": "galactic_skin", "name": "Galactic Skin", "cost": 500, "category": "Skin", "rarity": "LEGENDARY"},
    {"id": "cosmic_skin", "name": "Cosmic Skin", "cost": 800, "category": "Skin", "rarity": "LEGENDARY"},
    {"id": "scarf", "name": "Cozy Scarf", "cost": 350, "category": "Wearable", "rarity": "LEGENDARY"},
    {"id": "sunglasses", "name": "Neon Sunglasses", "cost": 450, "category": "Wearable", "rarity": "LEGENDARY"},
    {"id": "katana", "name": "Samurai Katana", "cost": 650, "category": "Wearable", "rarity": "LEGENDARY"},
    {"id": "sparkles", "name": "Hydro Sparkles", "cost": 550, "category": "Effect", "rarity": "LEGENDARY"},
]

SUPPORTED_COSMETICS = {item["id"] for item in REWARD_ITEMS}

BUDDY_EMOJIS = {
    "duckling": "🦆",
    "hatchling": "🐣",
    "swan": "🦢",
    "hero": "👑",
    "phoenix": "🦅",
    "robot": "🤖",
    "alien": "👾",
}

BUDDY_EXPRESSIONS = {
    "sad": "😢",
    "concerned": "😟",
    "hopeful": "🙂",
    "happy": "😊",
    "ecstatic": "🤩",
    "sleepy": "😴",
    "cool": "😎",
    "celebrating": "🥳",
    "thirsty": "😤",
    "neglected": "😭",
}

BUDDY_SPECIES_ART = {
    "duckling": "🦆",
    "hatchling": "🐥",
    "swan": "🦢",
    "hero": "🦸‍♂️",
    "phoenix": "🦅",
    "robot": "🤖",
    "alien": "👾",
    "dolphin": "🐬",
    "owl": "🦉",
    "fox": "🦊",
    "bunny": "🐰",
}

BUDDY_ENV_BACKGROUNDS = {
    "ocean": ("#0b2134", "#0b3f5d"),
    "space": ("#081024", "#2c1a47"),
    "forest": ("#0a2411", "#184725"),
    "cyber": ("#041118", "#10343f"),
    "desert": ("#2d1b05", "#7a5916"),
    "volcano": ("#2b1008", "#8f2a1a"),
}

BUDDY_ACCESSORY_LABELS = {
    "crown": "👑",
    "glasses": "🕶️",
    "cape": "🦸",
    "wings": "🪽",
    "halo": "👼",
}

THEME_BUDDIES = {
    "ocean": ("dolphin", "🐬"),
    "midnight": ("owl", "🦉"),
    "forest": ("fox", "🦊"),
    "cyber": ("robot", "🤖"),
    "sunset": ("phoenix", "🦅"),
    "day": ("bunny", "🐰"),
}


def get_buddy_avatar_html(buddy: dict[str, Any], theme: dict[str, str], progress_percent: int = 0) -> str:
    expression = get_buddy_expression(progress_percent)
    shop = st.session_state.data.get("shop", {})
    equipped = set(shop.get("equipped", []))
    skin = shop.get("skin", "classic")
    if skin == "galactic_skin":
        gradient_stops = '<stop offset="0%" stop-color="#f7b7ff"/><stop offset="55%" stop-color="#874cff"/><stop offset="100%" stop-color="#21104f"/>'
    elif skin == "cosmic_skin":
        gradient_stops = '<stop offset="0%" stop-color="#fff1a8"/><stop offset="55%" stop-color="#ff5e91"/><stop offset="100%" stop-color="#591b75"/>'
    else:
        gradient_stops = '<stop offset="0%" stop-color="#baf4ff"/><stop offset="55%" stop-color="#39c9f0"/><stop offset="100%" stop-color="#087ebd"/>'
    face = {
        "ecstatic": ('<circle cx="104" cy="123" r="7" fill="#123047"/><circle cx="156" cy="123" r="7" fill="#123047"/><path d="M105 145 Q130 168 155 145" fill="none" stroke="#123047" stroke-width="6" stroke-linecap="round"/>', "Full and glowing!"),
        "happy": ('<circle cx="104" cy="123" r="7" fill="#123047"/><circle cx="156" cy="123" r="7" fill="#123047"/><path d="M108 146 Q130 162 152 146" fill="none" stroke="#123047" stroke-width="6" stroke-linecap="round"/>', "Feeling refreshed!"),
        "hopeful": ('<circle cx="104" cy="123" r="7" fill="#123047"/><circle cx="156" cy="123" r="7" fill="#123047"/><path d="M112 148 Q130 156 148 148" fill="none" stroke="#123047" stroke-width="5" stroke-linecap="round"/>', "Keep sipping!"),
        "concerned": ('<circle cx="104" cy="125" r="7" fill="#123047"/><circle cx="156" cy="125" r="7" fill="#123047"/><path d="M108 154 Q130 138 152 154" fill="none" stroke="#123047" stroke-width="6" stroke-linecap="round"/>', "A little more water?"),
        "sad": ('<path d="M96 119 Q104 111 112 119" fill="none" stroke="#123047" stroke-width="5" stroke-linecap="round"/><path d="M148 119 Q156 111 164 119" fill="none" stroke="#123047" stroke-width="5" stroke-linecap="round"/><path d="M108 155 Q130 136 152 155" fill="none" stroke="#123047" stroke-width="6" stroke-linecap="round"/><path d="M99 130 Q96 143 101 148" fill="none" stroke="#55bfe9" stroke-width="5" stroke-linecap="round"/>', "I need a sip."),
    }[expression]
    svg = f'''
      <svg width="260" height="260" viewBox="0 0 260 260" xmlns="http://www.w3.org/2000/svg">
        <defs>
                    <linearGradient id="dropGradient" x1="25%" y1="5%" x2="80%" y2="100%">
                        {gradient_stops}
          </linearGradient>
          <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
            <feDropShadow dx="0" dy="0" stdDeviation="18" flood-color="{theme['accent']}" flood-opacity="0.4"/>
          </filter>
        </defs>
                <path d="M130 22 C130 22 58 106 58 156 C58 202 90 232 130 232 C170 232 202 202 202 156 C202 106 130 22 130 22Z" fill="url(#dropGradient)" filter="url(#glow)"/>
                <path d="M105 70 Q91 98 88 122" fill="none" stroke="#ffffff" stroke-width="12" stroke-linecap="round" opacity=".72"/>
                {face[0]}
                {('<path d="M84 116 L176 116 L166 142 L94 142 Z" fill="#17263c" stroke="#7df1ff" stroke-width="4"/><path d="M130 116 L130 142" stroke="#7df1ff" stroke-width="3"/>' if 'sunglasses' in equipped else '')}
                {('<path d="M84 116 L176 116 L166 142 L94 142 Z" fill="#8de9ff" fill-opacity=".9" stroke="#ffffff" stroke-width="3"/><path d="M130 116 L130 142" stroke="#2276d2" stroke-width="3"/><path d="M86 116 L74 111 M174 116 L186 111" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/>' if 'cooling_glasses' in equipped else '')}
                {('<path d="M70 174 Q130 154 190 174 L184 224 Q130 244 76 224 Z" fill="#ff8a65" stroke="#ffe0b2" stroke-width="3"/><path d="M130 165 L130 235 M82 190 L178 190" stroke="#fff3d6" stroke-width="5" opacity=".9"/>' if 'beach_shirt' in equipped else '')}
                {('<path d="M84 88 Q86 42 130 38 Q174 42 176 88 L164 98 L96 98 Z" fill="#f2c14e" stroke="#fff1a8" stroke-width="4"/><path d="M88 88 Q130 105 172 88" fill="none" stroke="#9b5c20" stroke-width="7"/>' if 'beanie' in equipped else '')}
                {('<path d="M82 166 Q130 187 178 166 L173 190 Q130 210 87 190 Z" fill="#ff6e8f" stroke="#ffd1dc" stroke-width="3"/><path d="M94 179 Q130 193 166 179" fill="none" stroke="#b51f58" stroke-width="4"/>' if 'scarf' in equipped else '')}
                {('<path d="M176 190 L232 70" stroke="#d9e7f4" stroke-width="7"/><path d="M171 195 L185 201 L194 186 L181 180 Z" fill="#8a5a32" stroke="#422811" stroke-width="3"/><path d="M204 110 L224 90" stroke="#ffffff" stroke-width="3"/>' if 'katana' in equipped else '')}
                {('<text x="32" y="70" font-size="28">✦</text><text x="214" y="100" font-size="24">✦</text><text x="28" y="190" font-size="20">✧</text><text x="222" y="210" font-size="26">✦</text>' if 'sparkles' in equipped else '')}
                <text x="130" y="270" text-anchor="middle" font-size="18" fill="{theme['text']}" font-family="Segoe UI, Arial, sans-serif">{face[1]}</text>
      </svg>
    '''
    return f'<img class="buddy-avatar-img" src="data:image/svg+xml;charset=utf-8,{quote(svg)}" alt="Buddy avatar" />'


def style_page(theme_name: str) -> dict[str, str]:
    theme = THEMES.get(theme_name, THEMES["ocean"])
    input_bg = theme['surface_alt']
    placeholder_color = 'rgba(13,31,56,0.45)' if theme_name == 'day' else 'rgba(255,255,255,0.65)'
    css = f"""
    <style>
    #MainMenu, footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{
        visibility: visible;
        height: 2.875rem !important;
        min-height: 2.875rem !important;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }}
    header[data-testid="stHeader"] > div {{
        height: 100% !important;
        min-height: 100% !important;
        overflow: visible !important;
    }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
    header button[aria-label*="sidebar" i] {{
        display: flex !important;
        position: fixed !important;
        top: 10px !important;
        left: 12px !important;
        overflow: visible !important;
        z-index: 1000000 !important;
        width: 36px !important;
        height: 36px !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 10px !important;
        background: {theme['surface']} !important;
        border: 1px solid {theme['border']} !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.2) !important;
    }}
    .css-18e3th9 {{ padding: 0rem 0rem 0rem 0rem; }}
    .css-1d391kg {{ padding: 0rem 0rem 0rem 0rem; }}
    .block-container {{ padding-top: 0rem; padding-bottom: 0rem; padding-left: 0rem; padding-right: 0rem; }}
    .stApp {{ background: {theme['background']} !important; color: {theme['text']} !important; }}
    body {{ background: {theme['background']} !important; color: {theme['text']} !important; }}
    .glass-panel {{ background: {theme['surface']}; border: 1px solid {theme['border']}; box-shadow: {theme['shadow']}; border-radius: 32px; backdrop-filter: blur(16px); padding: 24px; animation: fadeInUp 0.6s ease both; }}
    .glass-panel-alt {{ background: {theme['surface_alt']}; border: 1px solid {theme['border']}; box-shadow: {theme['shadow']}; border-radius: 28px; backdrop-filter: blur(14px); padding: 20px; animation: fadeInUp 0.6s ease both; }}
    .glass-pill {{ display:inline-flex; align-items:center; justify-content:center; gap:0.5rem; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); border-radius: 999px; color: {theme['text']}; padding: 10px 18px; font-weight: 600; animation: scaleIn 0.5s ease both; }}
    .glass-button {{ display:inline-flex; align-items:center; justify-content:center; gap:0.5rem; background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.16); color: {theme['text']}; border-radius: 18px; padding: 14px 20px; font-weight: 700; transition: transform 0.24s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.24s ease, box-shadow 0.24s ease; text-decoration: none; }}
    .glass-button:hover {{ transform: translateY(-6px) scale(1.02); background: rgba(255,255,255,0.18); box-shadow: 0 28px 60px rgba(0,0,0,0.22); }}
    .glass-button:active {{ transform: translateY(-2px) scale(0.98); }}
    .stButton>button, .stButton button {{ animation: pulse 4s ease-in-out infinite; border-radius: 18px; transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.18s ease, box-shadow 0.18s ease; color: {theme['text']} !important; background: rgba(255,255,255,0.12) !important; border: 1.5px solid rgba(255,255,255,0.2) !important; backdrop-filter: blur(10px); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08), 0 8px 20px rgba(0,0,0,0.1) !important; }}
    .stButton>button:hover, .stButton button:hover {{ transform: translateY(-4px) scale(1.05); box-shadow: 0 16px 40px rgba(0,0,0,0.2), inset 0 0 0 1px rgba(255,255,255,0.15) !important; background: rgba(255,255,255,0.18) !important; border-color: rgba(255,255,255,0.3) !important; }}
    .stTextInput>div>input, .stTextArea>div>textarea, .stNumberInput>div>input, .stSelectbox>div>div>div, .stFileUploader>div, input, textarea, select {{ color: {theme['text']} !important; background: {input_bg} !important; border: 1px solid {theme['border']} !important; transition: all 0.3s ease; }}
    .stTextInput>div>input::placeholder, .stTextArea>div>textarea::placeholder {{ color: {placeholder_color} !important; }}
    .stTextArea>div>textarea, textarea {{ min-height: 140px !important; }}
    .stSelectbox>div>div>div {{ background: {input_bg} !important; }}
    .buddy-avatar-img {{ width: 100%; max-width: 260px; border-radius: 28px; animation: zoomIn 0.7s ease both; }}
    .nav-shell {{ display:flex; flex-direction:column; gap: 12px; padding: 12px 0 0 0; }}
    .nav-shell button {{ border-radius: 22px; font-size: 1rem; padding: 14px 16px; background: rgba(255,255,255,0.12); border: 1.5px solid rgba(255,255,255,0.25); color: {theme['text']}; transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); animation: slideInLeft 0.5s ease both; backdrop-filter: blur(10px); cursor: pointer; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08); }}
    .nav-shell button:hover {{ transform: translateX(8px) scale(1.03); background: rgba(255,255,255,0.18); border-color: rgba(255,255,255,0.35); box-shadow: 0 12px 32px rgba(0,0,0,0.25), inset 0 0 0 1px rgba(255,255,255,0.12); }}
    .nav-shell button:active {{ transform: translateX(4px) scale(0.98); }}
    .nav-shell button:focus {{ outline: none; box-shadow: 0 0 0 3px rgba(56,209,246,0.42), inset 0 0 0 1px rgba(255,255,255,0.1); border-color: {theme['accent']}; }}
    .drawer-heading {{ animation: drawerReveal 0.28s ease both; transform-origin: left center; }}
    .daily-tip-card {{ animation: drawerReveal 0.5s ease both; }}
    
    .animated-card {{ animation: floatUp 1.2s cubic-bezier(0.34, 1.56, 0.64, 1) both; }}
    .hero-glow {{ animation: glowPulse 6s ease-in-out infinite; }}
    .liquid-bar {{ animation: fillUp 1.4s cubic-bezier(0.34, 1.56, 0.64, 1); }}
    .achievement-card, .glass-panel-alt, .mini-chart-card, .buddy-preview {{ animation: scaleAndFade 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) both; }}
    .achievement-card:nth-child(2) {{ animation-delay: 0.1s; }}
    .achievement-card:nth-child(3) {{ animation-delay: 0.2s; }}
    .achievement-card:nth-child(4) {{ animation-delay: 0.3s; }}
    .achievement-card:nth-child(5) {{ animation-delay: 0.4s; }}
    .achievement-card:nth-child(n+6) {{ animation-delay: 0.5s; }}
    .toast-banner {{ animation: slideDown 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both; }}
    .calendar-cell {{ animation: popIn 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) both; }}
    .calendar-cell:nth-child(2) {{ animation-delay: 0.05s; }}
    .calendar-cell:nth-child(3) {{ animation-delay: 0.1s; }}
    .calendar-cell:nth-child(4) {{ animation-delay: 0.15s; }}
    .calendar-cell:nth-child(5) {{ animation-delay: 0.2s; }}
    .calendar-cell:nth-child(6) {{ animation-delay: 0.25s; }}
    .calendar-cell:nth-child(n+7) {{ animation-delay: 0.3s; }}
    .buddy-avatar {{ animation: bounce 1.6s cubic-bezier(0.34, 1.56, 0.64, 1) infinite; }}
    
    @keyframes pulse {{ 0%,100% {{ transform: translateY(0); opacity: 1; }} 50% {{ transform: translateY(-3px); opacity: 0.95; }} }}
    @keyframes floatUp {{ 0% {{ transform: translateY(24px); opacity: 0; }} 100% {{ transform: translateY(0); opacity: 1; }} }}
    @keyframes glowPulse {{ 0%,100% {{ box-shadow: 0 0 80px rgba(56,209,246,0.12), 0 0 40px rgba(56,209,246,0.08); }} 50% {{ box-shadow: 0 0 120px rgba(56,209,246,0.22), 0 0 60px rgba(56,209,246,0.14); }} }}
    @keyframes fillUp {{ 0% {{ opacity: 0.3; transform: translateY(30px); }} 100% {{ opacity: 1; transform: translateY(0); }} }}
    @keyframes slideDown {{ 0% {{ opacity: 0; transform: translateY(-24px); }} 100% {{ opacity: 1; transform: translateY(0); }} }}
    @keyframes popIn {{ 0% {{ opacity: 0; transform: scale(0.85) translateY(10px); }} 50% {{ opacity: 1; }} 100% {{ opacity: 1; transform: scale(1) translateY(0); }} }}
    @keyframes bounce {{ 0%,100% {{ transform: translateY(0); }} 25% {{ transform: translateY(-8px); }} 50% {{ transform: translateY(-12px); }} 75% {{ transform: translateY(-4px); }} }}
    @keyframes scaleIn {{ 0% {{ transform: scale(0.9); opacity: 0; }} 100% {{ transform: scale(1); opacity: 1; }} }}
    @keyframes scaleAndFade {{ 0% {{ transform: scale(0.92) translateY(12px); opacity: 0; }} 100% {{ transform: scale(1) translateY(0); opacity: 1; }} }}
    @keyframes fadeInUp {{ 0% {{ transform: translateY(16px); opacity: 0; }} 100% {{ transform: translateY(0); opacity: 1; }} }}
    @keyframes zoomIn {{ 0% {{ transform: scale(0.88); opacity: 0; }} 50% {{ opacity: 0.7; }} 100% {{ transform: scale(1); opacity: 1; }} }}
    @keyframes slideInLeft {{ 0% {{ transform: translateX(-20px); opacity: 0; }} 100% {{ transform: translateX(0); opacity: 1; }} }}
    @keyframes drawerReveal {{ 0% {{ opacity: 0; transform: translateX(-18px); }} 100% {{ opacity: 1; transform: translateX(0); }} }}
    
    .nav-link {{ display:flex; align-items:center; justify-content:flex-start; gap: 14px; width:100%; min-width:0; text-decoration:none; color: {theme['text']}; padding: 14px 18px; border-radius: 24px; border: 1.5px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.08); transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); box-sizing:border-box; cursor: pointer; backdrop-filter: blur(12px); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05); }}
    .nav-link:hover {{ transform: translateX(6px) scale(1.02); background: rgba(255,255,255,0.16); border-color: rgba(255,255,255,0.3); box-shadow: 0 12px 32px rgba(0,0,0,0.2), inset 0 0 0 1px rgba(255,255,255,0.1); }}
    .nav-link.active {{ background: rgba(56,209,246,0.28); border-color: rgba(56,209,246,0.6); box-shadow: 0 0 24px rgba(56,209,246,0.25), inset 0 0 0 1px rgba(56,209,246,0.15); transform: translateX(2px); }}
    .nav-link span {{ white-space: nowrap; }}
    .nav-link .nav-icon {{ width: 28px; min-width: 28px; font-size: 1.15rem; display:inline-flex; align-items:center; justify-content:center; }}
    .nav-link .nav-label {{ flex:1; min-width:0; font-weight: 600; }}
    
    .hero-glow {{ position: relative; overflow: hidden; border-radius: 32px; }}
    .hero-glow::before {{ content: ""; position: absolute; top: -20%; left: -10%; width: 180%; height: 180%; background: radial-gradient(circle, rgba(56,209,246,0.18) 0%, transparent 55%); filter: blur(80px); pointer-events:none; animation: rotatePulse 12s ease-in-out infinite; }}
    @keyframes rotatePulse {{ 0% {{ transform: rotate(0deg) scale(1); }} 50% {{ transform: rotate(180deg) scale(1.1); }} 100% {{ transform: rotate(360deg) scale(1); }} }}
    
    .section-title {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 0.65rem; color: {theme['text']}; animation: slideInLeft 0.5s ease both; }}
    .section-subtitle {{ color: {theme['muted']}; margin-bottom: 1.6rem; animation: fadeInUp 0.6s ease 0.15s both; }}
    .stat-chip {{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding: 16px 20px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 22px; transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); animation: scaleAndFade 0.6s ease both; }}
    .stat-chip:hover {{ transform: translateY(-4px) scale(1.02); background: rgba(255,255,255,0.12); box-shadow: 0 12px 30px rgba(0,0,0,0.15); }}
    .stat-chip-title {{ color: {theme['muted']}; font-size: 0.92rem; }}
    .stat-chip-value {{ color: {theme['text']}; font-size: 1.35rem; font-weight: 700; }}
    
    .liquid-bar {{ position: relative; width: 100%; height: 220px; border-radius: 42px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); overflow:hidden; }}
    .liquid-fill {{ position:absolute; left:0; bottom:0; width:100%; background: linear-gradient(180deg, rgba(56,209,246,0.95), rgba(17,107,139,0.95)); transition: height 0.8s cubic-bezier(0.34, 1.56, 0.64, 1); }}
    .liquid-wave {{ position:absolute; left:0; bottom:0; width:200%; height: 70px; background: rgba(255,255,255,0.2); border-radius: 100%; opacity: 0.8; animation: wave 5s infinite linear; }}
    .liquid-wave:nth-child(2) {{ bottom: 18px; opacity: 0.6; animation-duration: 6.5s; animation-delay: -2s; }}
    @keyframes wave {{ 0%{{ transform: translateX(0); }} 100%{{ transform: translateX(-50%); }} }}
    
    .toast-banner {{ margin-bottom: 18px; padding: 16px 20px; border-radius: 26px; background: rgba(56,209,246,0.18); border: 1px solid rgba(56,209,246,0.35); color: {theme['text']}; display:flex; align-items:center; gap:12px; box-shadow: 0 8px 24px rgba(56,209,246,0.15); }}
    .achievement-card {{ border-radius: 28px; padding: 18px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }}
    .achievement-card:hover:not(.locked) {{ transform: translateY(-6px) scale(1.01); background: rgba(255,255,255,0.08); box-shadow: 0 12px 32px rgba(0,0,0,0.2), inset 0 0 0 1px rgba(255,255,255,0.05); }}
    .achievement-card.locked {{ filter: grayscale(0.55); opacity: 0.78; }}
    .reward-tag {{ display:inline-flex; align-items:center; gap:8px; padding: 8px 12px; border-radius: 16px; background: rgba(255,255,255,0.08); color: {theme['text']}; font-size: 0.85rem; transition: all 0.3s ease; }}
    .reward-tag:hover {{ transform: scale(1.05); background: rgba(255,255,255,0.12); }}
    
    .calendar-grid {{ display:grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 10px; }}
    .calendar-cell {{ border-radius: 20px; padding: 14px; min-height: 110px; display:flex; flex-direction:column; justify-content:space-between; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.05); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }}
    .calendar-cell:hover:not(.inactive) {{ transform: translateY(-4px) scale(1.02); background: rgba(255,255,255,0.08); box-shadow: 0 12px 28px rgba(0,0,0,0.15); }}
    .calendar-cell.inactive {{ opacity: 0.45; filter: blur(0.01rem); }}
    .progress-pill {{ display:inline-flex; align-items:center; gap:8px; padding: 8px 14px; border-radius: 999px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); transition: all 0.3s ease; animation: scaleIn 0.5s ease both; }}
    .nav-separator {{ height: 1px; width: 100%; background: rgba(255,255,255,0.08); margin: 18px 0; }}
    .mini-chart-card {{ border-radius: 24px; padding: 18px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }}
    .buddy-preview {{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; padding: 28px 20px; border-radius: 32px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }}
    .buddy-preview:hover {{ transform: translateY(-4px) scale(1.01); background: rgba(255,255,255,0.09); box-shadow: 0 16px 40px rgba(0,0,0,0.18); }}
    .buddy-avatar {{ font-size: 4.6rem; line-height: 1; }}
    .buddy-label {{ font-size: 1.05rem; color: {theme['muted']}; }}
    .buddy-status {{ display:flex; gap:12px; flex-wrap:wrap; }}
    .status-pill {{ padding: 10px 14px; border-radius: 999px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); font-size: 0.95rem; transition: all 0.3s ease; animation: popIn 0.5s ease both; }}
    .status-pill:hover {{ transform: scale(1.08); background: rgba(255,255,255,0.12); }}
    .dot-pill {{ width: 8px; height: 8px; border-radius: 999px; background: {theme['accent']}; display:inline-block; animation: pulse 2s ease-in-out infinite; }}
    .level-pill {{ display:inline-flex; align-items:center; gap:8px; padding: 10px 14px; border-radius: 999px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14); transition: all 0.3s ease; }}
    .detail-card {{ margin-top: 16px; padding: 18px; border-radius: 28px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); animation: fadeInUp 0.6s ease both; }}
    .goal-strip {{ display:flex; gap:10px; justify-content:space-between; align-items:center; margin-top:16px; }}
    .quarter-grid {{ display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    .quarter-cell {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 16px; text-align:center; transition: all 0.3s ease; animation: popIn 0.7s ease both; }}
    .quarter-cell:hover {{ transform: translateY(-3px) scale(1.02); background: rgba(255,255,255,0.1); }}
    .theme-swatch {{ width: 44px; height: 44px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.14); cursor: pointer; transition: all 0.3s ease; animation: scaleIn 0.5s ease both; }}
    .theme-swatch:hover {{ transform: scale(1.1); box-shadow: 0 8px 20px rgba(0,0,0,0.2); }}
    
    .settings-panel {{
      position: relative; width: 100%; background: rgba(255,255,255,0.08); border-top: 1px solid rgba(255,255,255,0.12);
      backdrop-filter: blur(20px); padding: 16px; margin-top: 12px; border-radius: 20px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }}
    
    .settings-header {{
      font-size: 1.35rem; font-weight: 800; margin-bottom: 12px; color: {theme['accent']};
    }}
    .settings-section {{
      margin-top: 28px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.12);
    }}
    .settings-section:first-of-type {{
      margin-top: 0; padding-top: 0; border-top: none;
    }}
    .settings-label {{
      font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; display: block;
    }}
    
    @media (max-width: 1100px) {{ .calendar-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }} }}
    @media (max-width: 840px) {{ .glass-panel, .glass-panel-alt {{ padding: 18px; }} .nav-shell {{ gap: 10px; }} }}
    @media (max-width: 720px) {{ .calendar-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .nav-link {{ padding: 14px 12px; }} }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    return theme


def get_current_page() -> str:
    """Get current page from query params or session state."""
    # Check query params first (most reliable)
    if "page" in st.query_params:
        page = st.query_params["page"]
    else:
        page = st.session_state.get("page", "Home")
    
    if page not in [item["id"] for item in NAV_ITEMS]:
        page = "Home"
    
    st.session_state["page"] = page
    return page


def query_page(page: str) -> None:
    """Navigate to a page using URL query parameters."""
    if page not in [item["id"] for item in NAV_ITEMS]:
        page = "Home"
    st.query_params["page"] = page
    st.session_state["page"] = page


def get_daily_tip() -> str:
    """Return one stable tip for the current calendar day."""
    return HYDRATION_TIPS[(date.today().day - 1) % len(HYDRATION_TIPS)]


def is_cosmetic_wearable(item_id: str) -> bool:
    return item_id in SUPPORTED_COSMETICS


def _safe_default_config(key: str, fallback: dict[str, Any]) -> dict[str, Any]:
    if isinstance(DEFAULT_DATA, dict):
        value = DEFAULT_DATA.get(key)
        if isinstance(value, dict):
            return value.copy()
    return fallback.copy()


def toggle_equipment_state(shop: dict[str, Any], item_id: str, category: str, equip: bool) -> dict[str, Any]:
    """Toggle an item as equipped or unequipped without leaking state across users."""
    shop = dict(shop or {})
    owned = list(shop.setdefault("owned", []))
    equipped = list(shop.setdefault("equipped", []))
    if category == "Skin":
        if equip and item_id in owned:
            shop["skin"] = item_id
        elif not equip:
            shop["skin"] = "classic"
        return shop

    if equip:
        if item_id in owned and item_id not in equipped:
            equipped.append(item_id)
    else:
        equipped = [entry for entry in equipped if entry != item_id]
    shop["equipped"] = equipped
    return shop


def render_authentication() -> bool:
    if st.session_state.get("authenticated", False):
        return True

    if not st.session_state.get("remembered_login_checked", False):
        st.session_state["remembered_login_checked"] = True
        remembered_username = load_remembered_login()
        if remembered_username and account_exists(remembered_username):
            st.session_state["authenticated"] = True
            st.session_state["username"] = remembered_username
            return True

    if not st.session_state.get("first_launch_checked", False):
        st.session_state["first_launch_checked"] = True
        browser_key = "water_buddy_app_first_launch"
        if "first_launch_done" not in st.session_state:
            st.session_state["first_launch_done"] = True
            st.session_state["first_launch_browser_key"] = browser_key
        if st.session_state.get("first_launch_browser_key") == browser_key:
            st.session_state["first_launch_done"] = True

    st.markdown("<div style='max-width:560px; margin:12vh auto 0; text-align:center;'><div style='font-size:4rem;'>💧</div><div class='section-title'>Welcome to Water Buddy</div><div class='section-subtitle'>Log in to keep your hydration journey private.</div></div>", unsafe_allow_html=True)
    login_tab, register_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True)
        if submitted:
            if verify_account(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username.strip().lower()
                remember_login(st.session_state["username"])
                st.rerun()
            st.error("Incorrect username or password.")
    with register_tab:
        with st.form("register_form"):
            username = st.text_input("Choose a username", key="register_username")
            password = st.text_input("Choose a password", type="password", key="register_password")
            confirm = st.text_input("Confirm password", type="password", key="register_confirm")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            normalized = username.strip().lower()
            if len(normalized) < 3 or not normalized.replace("_", "").replace("-", "").isalnum():
                st.error("Use at least 3 letters or numbers for your username.")
            elif len(password) < 8:
                st.error("Your password must be at least 8 characters.")
            elif password != confirm:
                st.error("The passwords do not match.")
            elif not create_account(normalized, password):
                st.error("That username already exists.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["username"] = normalized
                remember_login(normalized)
                st.success("Account created. Loading your private hydration space...")
                st.rerun()
    return False


def sync_theme_buddy(theme_name: str) -> None:
    buddy = st.session_state.data.setdefault("buddy", {})
    theme_buddy, _ = THEME_BUDDIES.get(theme_name, THEME_BUDDIES["ocean"])
    buddy["species"] = theme_buddy
    buddy["theme_buddy"] = theme_buddy


def init_state() -> None:
    if "data" not in st.session_state:
        data = load_data(username=st.session_state["username"])
        data["profile"].setdefault("name", "")
        data["profile"].setdefault("gender", "Prefer not to say")
        data["profile"].setdefault("onboarding_complete", False)
        data["profile"].setdefault("goal", calculate_hydration_goal(
            data["profile"].get("age", 25),
            data["profile"].get("weight", 70),
            data["profile"].get("activity", "moderate"),
            data["profile"].get("climate", "warm"),
        ))
        data["profile"].setdefault("custom_goal", None)
        data["profile"].setdefault("occupation", "Student")
        data.setdefault("settings", _safe_default_config("settings", {
            "theme": "ocean",
            "notifications": True,
            "auto_save": True,
            "hide_tips": False,
            "reminder_interval_minutes": 60,
            "reminder_amount_ml": 250,
        }))
        data.setdefault("buddy", _safe_default_config("buddy", {
            "species": "duckling",
            "eyes": "sparkle",
            "mouth": "smile",
            "name": "Buddy",
            "custom_emoji": "",
            "accessories": [],
            "environment": "ocean",
            "mood": "happy",
        }))
        data.setdefault("shop", _safe_default_config("shop", {
            "owned": ["default"],
            "selected": "default",
            "equipped": [],
            "skin": "classic",
        }))
        data.setdefault("quests_claimed", [])
        data.setdefault("stats", _safe_default_config("stats", {
            "points": 0,
            "streak": 0,
            "coins": 0,
            "achievements": [],
        }))
        evaluate_achievements(data)
        st.session_state.data = data
        st.session_state.toast_message = ""
        st.session_state.verify_result = None
        st.session_state.verify_path = None
        st.session_state["page"] = "Home"


def refresh_for_new_day() -> None:
    """Reload the account after midnight while keeping the user signed in."""
    today_key = date.today().isoformat()
    if st.session_state.get("app_date") == today_key:
        return
    st.session_state["app_date"] = today_key
    st.session_state["data"] = load_data(username=st.session_state["username"])
    st.session_state.pop("last_reminder_alert", None)
    st.session_state.pop("show_drop_celebration", None)
    st.session_state["page"] = "Home"


def schedule_midnight_refresh() -> None:
    """Refresh the browser shortly after the next local midnight."""
    now = datetime.now()
    next_midnight = (now + __import__("datetime").timedelta(days=1)).replace(
        hour=0, minute=0, second=1, microsecond=0
    )
    delay_ms = max(1000, int((next_midnight - now).total_seconds() * 1000))
    components.html(
        f"<script>setTimeout(() => window.parent.location.reload(), {delay_ms});</script>",
        height=0,
    )


def save_data_state(message: str | None = None) -> None:
    save_data(st.session_state.data, st.session_state["username"])
    evaluate_achievements(st.session_state.data)
    if message:
        st.session_state.toast_message = message


def reset_all_data(message: str = "All progress reset.") -> None:
    """Reset the complete profile and progress so onboarding starts again."""
    st.session_state.data = copy.deepcopy(DEFAULT_DATA)
    st.session_state.data["profile"]["onboarding_complete"] = False
    save_data_state(message)
    
def render_reset_all_action(label: str, key: str, message: str, page: str | None = None) -> None:
    """Require confirmation before deleting the account's complete progress."""
    confirm_key = f"confirm_{key}"
    if not st.session_state.get(confirm_key, False):
        if st.button(label, key=key, use_container_width=True):
            st.session_state[confirm_key] = True
            st.rerun()
        return

    st.warning("Are you sure you want to clear all data? You will lose your hydration progress, streaks, coins, Buddy items, and settings.")
    confirm_cols = st.columns(2)
    with confirm_cols[0]:
        if st.button("Yes, clear all data", key=f"{key}_confirm", use_container_width=True):
            reset_all_data(message)
            st.session_state.pop(confirm_key, None)
            if page:
                query_page(page)
            st.rerun()
    with confirm_cols[1]:
        if st.button("Cancel", key=f"{key}_cancel", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()


def add_entry(amount: int, drink: str, notes: str = "") -> None:
    today_key = date.today().strftime("%Y-%m-%d")
    entry = {
        "date": today_key,
        "time": datetime.now().strftime("%H:%M"),
        "drink": drink,
        "amount": amount,
        "notes": notes,
        "verified": False,
    }
    st.session_state.data["entries"].append(entry)
    st.session_state["show_drop_celebration"] = True
    st.session_state.pop("last_reminder_alert", None)
    stats = st.session_state.data.setdefault("stats", {})
    stats["points"] = sum(e["amount"] // 100 for e in st.session_state.data["entries"])
    stats["streak"] = calculate_streak(st.session_state.data["entries"])
    stats["coins"] = stats.get("coins", 0) + 1
    save_data_state(f"Hydration +{amount} ml — earned +10 XP, +1 Aqua Coin")


def recalculate_hydration_stats() -> None:
    """Keep hydration-derived stats consistent after an edit or reset."""
    entries = st.session_state.data.setdefault("entries", [])
    stats = st.session_state.data.setdefault("stats", {})
    stats["points"] = sum(max(0, int(entry.get("amount", 0))) // 100 for entry in entries)
    stats["streak"] = calculate_streak(entries)


def undo_last_entry() -> bool:
    """Remove the most recent drink log without changing app settings."""
    entries = st.session_state.data.setdefault("entries", [])
    if not entries:
        return False
    removed = entries.pop()
    stats = st.session_state.data.setdefault("stats", {})
    stats["coins"] = max(0, stats.get("coins", 0) - 1)
    recalculate_hydration_stats()
    save_data_state(f"Removed the last log: -{removed.get('amount', 0)} ml.")
    return True


def reset_hydration_logs() -> None:
    """Clear drink logs and derived hydration progress while preserving settings."""
    st.session_state.data["entries"] = []
    recalculate_hydration_stats()
    save_data_state("Hydration logs reset. Your settings and Buddy were kept.")


def get_today_entries() -> list[dict[str, Any]]:
    today_key = date.today().strftime("%Y-%m-%d")
    return [e for e in st.session_state.data.get("entries", []) if e.get("date") == today_key]


def get_today_summary() -> tuple[int, int, int]:
    entries = get_today_entries()
    total = sum(e.get("amount", 0) for e in entries)
    unique = len({e.get("drink", "water") for e in entries})
    verified = sum(1 for e in entries if e.get("verified"))
    return total, unique, verified


def get_active_goal() -> int:
    profile = st.session_state.data.get("profile", {})
    custom_goal = profile.get("custom_goal")
    if custom_goal and isinstance(custom_goal, int) and custom_goal > 0:
        return custom_goal
    return profile.get("goal", 2600)


def get_buddy_state() -> dict[str, str]:
    buddy = st.session_state.data.get("buddy", DEFAULT_DATA["buddy"].copy())
    mood = buddy.get("mood", "happy")
    expression = get_buddy_expression(get_today_progress_percent())
    status_message = {
        "ecstatic": "Goal complete!",
        "happy": "Feeling refreshed!",
        "hopeful": "Keep sipping!",
        "concerned": "A little more water?",
        "sad": "I need a sip.",
    }[expression]
    buddy_name = buddy.get("name", "Buddy")
    return {"emoji": "💧", "expression": expression, "name": buddy_name, "status_message": status_message, **buddy}


def get_buddy_expression(progress_percent: int) -> str:
    """Return the Buddy expression for each 25% hydration milestone."""
    progress = max(0, min(100, int(progress_percent)))
    if progress >= 100:
        return "ecstatic"
    if progress >= 75:
        return "happy"
    if progress >= 50:
        return "hopeful"
    if progress >= 25:
        return "concerned"
    return "sad"


def get_today_progress_percent() -> int:
    intake, _, _ = get_today_summary()
    return get_progress_percent(get_active_goal(), intake)


def get_hydration_reminder() -> tuple[bool, str, str]:
    settings = st.session_state.data.get("settings", {})
    if not settings.get("notifications", True):
        return False, "", ""
    interval = max(15, int(settings.get("reminder_interval_minutes", 60)))
    amount = max(50, int(settings.get("reminder_amount_ml", 250)))
    entries = get_today_entries()
    now = datetime.now()
    if entries:
        latest = max(entries, key=lambda entry: entry.get("time", "00:00"))
        try:
            last_drink = datetime.strptime(f"{date.today().isoformat()} {latest['time']}", "%Y-%m-%d %H:%M")
        except (KeyError, ValueError):
            last_drink = now
    else:
        last_drink = now.replace(hour=8, minute=0, second=0, microsecond=0)
    due = now >= last_drink + __import__("datetime").timedelta(minutes=interval)
    if due:
        return True, f"Time to hydrate. Take about {amount} ml now.", f"Drink {amount} ml"
    next_time = last_drink + __import__("datetime").timedelta(minutes=interval)
    return False, "", f"Next reminder at {next_time.strftime('%H:%M')}"


def render_home_reminder(theme: dict[str, str]) -> None:
    due, message, action_label = get_hydration_reminder()
    if not due:
        return
    reminder_token = f"{date.today().isoformat()}:{message}"
    if st.session_state.get("last_reminder_alert") != reminder_token:
        st.toast(f"💧 {message}", icon="💧")
        st.session_state["last_reminder_alert"] = reminder_token
    st.warning(f"💧 {message}")
    if st.button(action_label, key="home_reminder_add", use_container_width=False):
        amount = int(st.session_state.data.get("settings", {}).get("reminder_amount_ml", 250))
        add_entry(amount, "water", "Reminder")
        st.toast("Hydration logged. Nice work!", icon="💧")
        st.rerun()


def apply_buddy_mood() -> None:
    progress = get_today_progress_percent()
    streak = st.session_state.data["stats"].get("streak", 0)
    if progress >= 100:
        st.session_state.data["buddy"]["mood"] = "ecstatic"
    elif streak >= 7:
        st.session_state.data["buddy"]["mood"] = "cool"
    else:
        st.session_state.data["buddy"]["mood"] = get_buddy_expression(progress)


def render_left_settings_panel(active_page: str, theme: dict[str, str]) -> None:
    """Render the persistent left navigation drawer."""
    with st.sidebar:
        st.markdown(
            f"<div class='drawer-heading' style='font-size:1.55rem; font-weight:700; color:{theme['text']}; padding:8px 0 18px;'>💧 Water Buddy</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<div class='drawer-heading'><label class='settings-label' style='color:{theme['accent']};'>PAGES</label></div>", unsafe_allow_html=True)
        for item in NAV_ITEMS:
            is_active = item["id"] == active_page
            label = f"{item['icon']} {item['label']}" + (" ✓" if is_active else "")
            if st.button(label, key=f"nav_btn_{item['id']}_v2", use_container_width=True):
                query_page(item["id"])
                st.rerun()

        st.divider()
        st.markdown(f"<label class='settings-label' style='color:{theme['accent']};'>QUICK LINKS</label>", unsafe_allow_html=True)
        quick_cols = st.columns(2)
        with quick_cols[0]:
            if st.button("⚙️ Settings", key="nav_settings_menu", use_container_width=True):
                query_page("Settings")
                st.rerun()
        with quick_cols[1]:
            if st.button("📊 Analytics", key="nav_analytics_menu", use_container_width=True):
                query_page("Analytics")
                st.rerun()
        if st.button("🚪 Log out / Switch account", key="logout_button", use_container_width=True):
            forget_login()
            for key in ["authenticated", "username", "data", "hydrocoach_messages"]:
                st.session_state.pop(key, None)
            st.session_state.pop("remembered_login_checked", None)
            st.rerun()


def render_nav(active_page: str, theme: dict[str, str]) -> None:
    """Navigation is now in the left sidebar - this is a placeholder."""
    pass  # Navigation handled in render_left_settings_panel


def render_toast() -> None:
    message = st.session_state.get("toast_message", "")
    if message:
        st.markdown(f"<div class='toast-banner'>💧 {message}</div>", unsafe_allow_html=True)
        st.session_state.toast_message = ""


def render_water_drop_celebration() -> None:
    if not st.session_state.pop("show_drop_celebration", False):
        return
    drops = "".join(
        f"<span class='celebration-drop drop-{index}'>&#128167;</span>"
        for index in range(18)
    )
    components.html(
        f"""
        <style>
          .drop-celebration {{ position: fixed; inset: 0; z-index: 999999; pointer-events: none; overflow: hidden; }}
          .celebration-drop {{ position: absolute; top: -48px; color: #54d9f5; font-size: 24px; filter: drop-shadow(0 4px 8px rgba(18, 175, 225, .45)); animation: fall 1.8s cubic-bezier(.2,.7,.4,1) forwards; opacity: 0; }}
          .drop-0 {{ left: 4%; animation-delay: .02s; }} .drop-1 {{ left: 10%; animation-delay: .18s; }}
          .drop-2 {{ left: 16%; animation-delay: .08s; }} .drop-3 {{ left: 23%; animation-delay: .28s; }}
          .drop-4 {{ left: 30%; animation-delay: .12s; }} .drop-5 {{ left: 37%; animation-delay: .36s; }}
          .drop-6 {{ left: 44%; animation-delay: .05s; }} .drop-7 {{ left: 51%; animation-delay: .22s; }}
          .drop-8 {{ left: 58%; animation-delay: .32s; }} .drop-9 {{ left: 65%; animation-delay: .1s; }}
          .drop-10 {{ left: 72%; animation-delay: .26s; }} .drop-11 {{ left: 79%; animation-delay: .04s; }}
          .drop-12 {{ left: 85%; animation-delay: .2s; }} .drop-13 {{ left: 91%; animation-delay: .34s; }}
          .drop-14 {{ left: 27%; animation-delay: .42s; }} .drop-15 {{ left: 48%; animation-delay: .48s; }}
          .drop-16 {{ left: 68%; animation-delay: .4s; }} .drop-17 {{ left: 96%; animation-delay: .16s; }}
          @keyframes fall {{ 0% {{ transform: translateY(0) rotate(0deg); opacity: 0; }} 12% {{ opacity: 1; }} 100% {{ transform: translateY(105vh) rotate(18deg); opacity: 0; }} }}
        </style>
        <div class="drop-celebration">{drops}</div>
        """,
        height=1,
        scrolling=False,
    )


def get_user_name() -> str:
    name = st.session_state.data.get("profile", {}).get("name", "")
    return name.strip() or "Hydration Champion"


def render_welcome_header(theme: dict[str, str]) -> None:
    st.markdown(
        f"<div class='glass-panel-alt' style='margin: 8px 0 18px; padding: 16px 22px; font-size: 1.25rem; font-weight: 700;'>Welcome {get_user_name()} <span style='color:{theme['accent']};'>💧</span></div>",
        unsafe_allow_html=True,
    )


def render_onboarding(theme: dict[str, str]) -> None:
    profile = st.session_state.data["profile"]
    st.markdown(
        "<div style='max-width:760px; margin: 8vh auto 0; text-align:center;'><div style='font-size:4rem;'>💧</div><div class='section-title'>Welcome to Water Buddy</div><div class='section-subtitle'>Tell us a little about yourself so your hydration journey feels personal.</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='glass-panel' style='max-width:760px; margin: 24px auto;'>", unsafe_allow_html=True)
    name = st.text_input("Your name", value=profile.get("name", ""), placeholder="Enter your name")
    cols = st.columns(2)
    with cols[0]:
        gender_options = ["Female", "Male", "Non-binary", "Prefer not to say"]
        current_gender = profile.get("gender", "Prefer not to say")
        gender = st.selectbox("Gender", gender_options, index=gender_options.index(current_gender) if current_gender in gender_options else gender_options.index("Prefer not to say"))
        age = st.number_input("Age", min_value=5, max_value=120, value=int(profile.get("age", 25) or 25), step=1)
        weight = st.number_input("Weight (kg)", min_value=30, max_value=200, value=int(profile.get("weight", 70) or 70), step=1)
        activity = st.selectbox("Activity level", ["low", "moderate", "high", "very_high"], index=["low", "moderate", "high", "very_high"].index(profile.get("activity", "moderate")))
    with cols[1]:
        occupations = get_all_occupations()
        current_occupation = profile.get("occupation", "Student")
        occupation = st.selectbox("Occupation", occupations, index=occupations.index(current_occupation) if current_occupation in occupations else occupations.index("Student"))
        climate = st.selectbox("Climate", ["cool", "warm", "hot"], index=["cool", "warm", "hot"].index(profile.get("climate", "warm")))
        custom_goal = st.number_input("Custom daily goal (ml)", min_value=0, max_value=5000, value=int(profile.get("custom_goal") or 0), step=50)

        age_rec = get_age_recommendation(age)
        occ_rec = get_occupation_recommendation(occupation)
        climate_rec = get_climate_recommendation(climate)
        recommendation_cards = [
            ("age", f"👤 Age Group ({age_rec['age_range']})", age_rec["recommended_ml"], f"≈ {age_rec['cups_per_day']} cups per day", age_rec["hydration_tips"]),
            ("occupation", f"{occ_rec['icon']} {occupation}", occ_rec["recommended_ml"], occ_rec["note"], occ_rec["tips"]),
            ("climate", f"🌡️ {climate.title()} Climate", climate_rec["recommended_ml"], climate_rec["note"], climate_rec["tips"]),
        ]
        st.markdown(f"<div style='font-weight:700; margin: 18px 0 12px; font-size:1.1rem;'>📊 Personalized Recommendations</div>", unsafe_allow_html=True)
        rec_cols = st.columns(3)
        for column, (key, title, recommended_ml, detail, tip) in zip(rec_cols, recommendation_cards):
            with column:
                st.markdown(
                    f"<div class='glass-panel-alt' style='min-height:220px;'><div style='font-weight:700; margin-bottom:8px;'>{title}</div>"
                    f"<div style='font-size:1.3rem; font-weight:700; color:{theme['accent']}; margin-bottom:8px;'>{recommended_ml} ml/day</div>"
                    f"<div style='color:{theme['muted']}; font-size:0.85rem; margin-bottom:8px;'>{detail}</div>"
                    f"<div style='margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1); font-size:0.85rem;'><strong>💡 Tip:</strong> {tip}</div></div>",
                    unsafe_allow_html=True,
                )
        average_recommendation = round(sum(card[2] for card in recommendation_cards) / len(recommendation_cards))
        st.markdown(f"<div class='glass-panel-alt' style='margin-top:18px;'><div style='font-weight:700;'>🎯 Recommended daily goal</div><div style='font-size:1.5rem; font-weight:800; color:{theme['accent']}; margin-top:10px;'>{average_recommendation:,} ml/day</div><div style='color:{theme['muted']}; margin-top:6px;'>This is the average of your age, occupation, and climate guidance.</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    with st.form("onboarding_actions"):
        submit_cols = st.columns(2)
        with submit_cols[0]:
            submitted = st.form_submit_button("Start my hydration journey", use_container_width=True)
        with submit_cols[1]:
            skipped = st.form_submit_button("Skip for now", use_container_width=True)

    if submitted or skipped:
        profile["name"] = name.strip()
        profile["gender"] = gender
        profile["age"] = age
        profile["weight"] = weight
        profile["activity"] = activity
        profile["occupation"] = occupation
        profile["climate"] = climate
        profile["custom_goal"] = custom_goal or None
        profile["goal"] = profile["custom_goal"] or calculate_hydration_goal(age, weight, activity, climate, occupation)
        profile["onboarding_complete"] = True
        save_data_state("Welcome to Water Buddy!")
        st.rerun()


def render_progress_hero(goal: int, intake: int, theme: dict[str, str]) -> None:
    pct = int(min(100, (intake / goal) * 100)) if goal else 0
    remaining = max(0, goal - intake)
    hero_html = f"""
    <div class='glass-panel hero-glow'>
      <div style='display:flex; justify-content:space-between; align-items:flex-start; gap:24px;'>
        <div>
          <div style='color: {theme['accent']}; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 1px;'>Good morning, {get_user_name()}</div>
          <div style='font-size: 2.7rem; font-weight: 800; margin-top: 12px;'>Stay locked in.</div>
          <div style='color: {theme['muted']}; font-size: 1rem; margin-top: 12px;'>Your buddy is cheering you on — keep the liquid level rising.</div>
        </div>
        <div style='display:flex; flex-direction:column; align-items:flex-end; gap:8px;'>
          <div class='glass-pill'>🔥 {st.session_state.data['stats'].get('streak', 0)} Day Streak</div>
          <div class='glass-pill'>⭐ Level {get_level_info(st.session_state.data['stats'].get('points', 0))['level']}</div>
          <div class='glass-pill'>💎 {st.session_state.data['stats'].get('coins', 0)} Aqua Coins</div>
        </div>
      </div>
      <div style='margin-top: 32px;'>
        <div style='display:flex; justify-content:space-between; align-items:center; gap:18px;'>
          <div>
            <div style='font-size: 2.9rem; font-weight: 800;'>{intake:,} ml</div>
            <div style='color: {theme['muted']}; margin-top: 6px;'>of {goal:,} ml</div>
          </div>
          <div style='text-align:right;'>
            <div style='font-size: 1rem; color: {theme['muted']};'>Remaining</div>
            <div style='font-size: 2rem; font-weight:800;'>{remaining:,} ml</div>
          </div>
        </div>
        <div class='liquid-bar' style='margin-top: 24px;'>
          <div class='liquid-fill' style='height: {pct}%;'></div>
          <div class='liquid-wave'></div>
          <div class='liquid-wave'></div>
          <div style='position:absolute; top: 18px; left: 22px; color: {theme['text']}; font-weight:700;'>Progress</div>
          <div style='position:absolute; top: 18px; right: 22px; color: {theme['accent']}; font-weight:700;'>{pct}%</div>
        </div>
      </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)


def render_stat_chips(goal: int, intake: int, unique: int, verified: int, theme: dict[str, str]) -> None:
    balance = max(0, goal - intake)
    percent = get_progress_percent(goal, intake)
    chips_html = f"""
      <div class='glass-panel-alt' style='display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;'>
        <div class='stat-chip'><div><div class='stat-chip-title'>Hydration Left</div><div class='stat-chip-value'>{balance:,} ml</div></div></div>
        <div class='stat-chip'><div><div class='stat-chip-title'>Unique Drinks</div><div class='stat-chip-value'>{unique}</div></div></div>
        <div class='stat-chip'><div><div class='stat-chip-title'>Verified Logs</div><div class='stat-chip-value'>{verified}</div></div></div>
        <div class='stat-chip'><div><div class='stat-chip-title'>XP Progress</div><div class='stat-chip-value'>{get_level_info(st.session_state.data['stats'].get('points', 0))['xp_progress_pct']}%</div></div></div>
        <div class='stat-chip'><div><div class='stat-chip-title'>Goal Progress</div><div class='stat-chip-value'>{percent}%</div></div></div>
      </div>
    """
    st.markdown(chips_html, unsafe_allow_html=True)


def render_timeline(theme: dict[str, str]) -> None:
    entries = get_today_entries()[::-1]
    if not entries:
        st.markdown("<div class='glass-panel-alt'><div style='color: rgba(255,255,255,0.75);'>No drinks logged yet — your timeline will appear here once you hydrate.</div></div>", unsafe_allow_html=True)
        return
    rows = []
    for entry in entries[:6]:
        rows.append(f"<div style='display:flex; justify-content:space-between; align-items:center; padding: 14px 0; border-bottom: 1px solid rgba(255,255,255,0.08);'><div><span style='font-size:0.95rem; color:{theme['muted']};'>{entry['time']}</span><div style='font-size:1rem; font-weight:700; margin-top:4px; color: {theme['text']};'>{entry['drink'].title()} — {entry['amount']} ml</div></div><div style='font-size:1.2rem;'>💧</div></div>")
    timeline_html = f"""
      <div class='glass-panel-alt'>
        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;'><div style='font-weight:700;'>Hydration Timeline</div><div style='color:{theme['muted']};'>Today's journey</div></div>
        {''.join(rows)}
      </div>
    """
    st.markdown(timeline_html, unsafe_allow_html=True)


def render_home(theme: dict[str, str]) -> None:
    goal = get_active_goal()
    intake, unique_drinks, verified_count = get_today_summary()
    
    # Day/Night Mode Toggle and Reset Button at top with enhanced styling
    st.markdown(f"<div style='margin-bottom: 16px;'><label class='settings-label'>QUICK ACTIONS</label></div>", unsafe_allow_html=True)
    action_cols = st.columns(3)
    
    with action_cols[0]:
        if st.button("🌙 Night Mode", key="mode_night_home", use_container_width=True):
            dark_themes = ["ocean", "midnight", "forest", "cyber", "sunset"]
            current = st.session_state.data["settings"].get("theme", "ocean")
            if current not in dark_themes:
                st.session_state.data["settings"]["theme"] = "ocean"
            st.rerun()
    
    with action_cols[1]:
        if st.button("☀️ Day Mode", key="mode_day_home", use_container_width=True):
            st.session_state.data["settings"]["theme"] = "day"
            st.rerun()
    
    with action_cols[2]:
        render_reset_all_action("🔄 Reset All Data", "reset_home", "✅ All data has been reset!")
    
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    
    render_progress_hero(goal, intake, theme)
    render_home_reminder(theme)
    render_stat_chips(goal, intake, unique_drinks, verified_count, theme)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    with st.container():
        cols = st.columns([2, 1])
        with cols[0]:
            st.markdown("<div class='section-title'>Quick Add</div>", unsafe_allow_html=True)
            preset_cols = st.columns(5)
            for idx, value in enumerate([100, 250, 330, 500, 750]):
                if preset_cols[idx].button(f"+{value} ml", key=f"quick_{value}"):
                    add_entry(value, "water", "Quick add")
                    st.rerun()
            st.markdown("<div style='margin-top: 18px; color: rgba(255,255,255,0.7);'>💡 Hydrate faster with tactile quick-add buttons that reward every sip.</div>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown("<div class='glass-panel'><div style='font-size:1rem; font-weight:700; margin-bottom:10px;'>HydroCoach</div><div style='margin-bottom:14px; color: rgba(255,255,255,0.75);'>" + get_coach().get_tip(st.session_state.data) + "</div><div class='glass-pill'>Ask me anything or let me suggest your next sip.</div></div>", unsafe_allow_html=True)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    with st.container():
        cols = st.columns([2, 1])
        with cols[0]:
            st.markdown("<div class='section-title'>Today’s Timeline</div>", unsafe_allow_html=True)
            render_timeline(theme)
        with cols[1]:
            buddy = get_buddy_state()
            buddy_html = f"""
              <div class='buddy-preview'>
                                <div class='buddy-avatar'>{get_buddy_avatar_html(buddy, theme, get_today_progress_percent())}</div>
                <div style='font-size:1.45rem; font-weight:700;'>Buddy is {buddy['expression']}</div>
                                <div class='buddy-label'>Level {get_level_info(st.session_state.data['stats'].get('points', 0))['level']} • Water Drop Buddy</div>
                <div class='buddy-status'>
                  <span class='status-pill'>Mood: {buddy['mood'].title()}</span>
                  <span class='status-pill'>XP: {st.session_state.data['stats'].get('points', 0)}</span>
                  <span class='status-pill'>Coins: {st.session_state.data['stats'].get('coins', 0)}</span>
                </div>
              </div>
            """
            st.markdown(buddy_html, unsafe_allow_html=True)
            cols = st.columns(2)
            if cols[0].button('💬 Talk', key='home_talk', use_container_width=True):
                query_page('Buddy')
                st.rerun()
            if cols[1].button('🎨 Customize', key='home_customize', use_container_width=True):
                query_page('Buddy')
                st.rerun()
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>💡 Daily hydration tip</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='glass-panel-alt daily-tip-card'><div style='font-weight:700; color:{theme['accent']};'>Day {date.today().day} of your hydration month</div><div style='color:{theme['muted']}; margin-top:10px;'>{get_daily_tip()}</div></div>",
        unsafe_allow_html=True,
    )


def get_quest_progress(quest_id: str) -> tuple[int, int, bool]:
    today_goal = st.session_state.data["profile"].get("goal", 2600)
    intake, _, verified_count = get_today_summary()
    streak = st.session_state.data["stats"].get("streak", 0)
    if quest_id == "daily_goal":
        current = min(intake, today_goal)
        target = today_goal
    elif quest_id == "weekly_streak":
        current = min(streak, 7)
        target = 7
    elif quest_id == "verify_bottles":
        current = min(verified_count, 5)
        target = 5
    else:
        current = 0
        target = 1
    completed = current >= target
    return current, target, completed


def claim_quest(quest_id: str, reward: dict[str, int]) -> None:
    claimed = st.session_state.data.setdefault("quests_claimed", [])
    if quest_id in claimed:
        return
    claimed.append(quest_id)
    stats = st.session_state.data.setdefault("stats", {})
    stats["points"] = stats.get("points", 0) + reward.get("xp", 0)
    stats["coins"] = stats.get("coins", 0) + reward.get("coins", 0)
    save_data_state(f"Quest claimed: +{reward['xp']} XP, +{reward['coins']} Aqua Coins")


def render_quests(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title' style='animation: slideInLeft 0.5s ease both;'>🎯 Daily Quests</div><div class='section-subtitle'>Small missions that keep hydration fun.</div>", unsafe_allow_html=True)
    for idx, quest in enumerate(QUESTS):
        current, target, completed = get_quest_progress(quest["id"])
        claimed = quest["id"] in st.session_state.data.get("quests_claimed", [])
        progress_pct = int((current / target) * 100) if target else 0
        status_label = "✓ Completed" if completed else "📍 In progress"
        claim_html = f"<div class='glass-panel-alt' style='animation: slideInLeft 0.5s ease both; animation-delay: {idx * 0.1}s;'><div style='display:flex; justify-content:space-between; gap:18px; align-items:center;'><div><div style='font-weight:700;'>{quest['title']}</div><div style='color:{theme['muted']}; margin-top:6px;'>{quest['subtitle']}</div></div><div style='text-align:right;'><div class='reward-tag'>+{quest['reward']['xp']} XP</div><div class='reward-tag'>+{quest['reward']['coins']} 💎</div></div></div><div style='margin-top:18px;'><div class='progress-pill'><span>{current}/{target}</span><span>{status_label}</span></div></div></div>"""
        st.markdown(claim_html, unsafe_allow_html=True)
        if completed and not claimed:
            if st.button(f"✓ Claim {quest['title']}", key=f"claim_{quest['id']}", use_container_width=True):
                claim_quest(quest["id"], quest["reward"])
                st.rerun()
        elif claimed:
            st.markdown(f"<div style='margin-top:12px; color: rgba(56,209,246,0.9); font-weight:700;'>✅ Already claimed!</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)


def render_achievements(theme: dict[str, str]) -> None:
    st.markdown(f"<div class='section-title' style='animation: slideInLeft 0.5s ease both;'>🏆 Achievement Hall</div><div class='section-subtitle'>Collect badges, unlock rarities, and watch your progress shine.</div>", unsafe_allow_html=True)
    unlocked = set(st.session_state.data.get("stats", {}).get("achievements", []))
    
    # Build grid HTML
    grid_items_html = []
    for idx, ach in enumerate(ACHIEVEMENT_DEFINITIONS):
        earned = ach["id"] in unlocked
        rarity_color = {
            "COMMON": "#7df1ff",
            "RARE": "#9d7cff",
            "EPIC": "#ff8c9e",
            "LEGENDARY": "#ffd56e",
        }.get(ach["rarity"], theme["accent"])
        status = "🔓 Unlocked" if earned else "🔒 Locked"
        opacity = "1" if earned else "0.65"
        status_color = theme['accent'] if earned else theme['muted']
        card_class = "achievement-card locked" if not earned else "achievement-card"
        delay = idx * 0.08
        
        card_html = f"<div class='{card_class}' style='opacity:{opacity}; animation: scaleAndFade 0.6s ease both; animation-delay: {delay}s;'>"
        card_html += f"<div style='display:flex; align-items:center; justify-content:space-between; gap:16px;'>"
        card_html += f"<div style='font-size:1.8rem;'>{ach['emoji']}</div>"
        card_html += f"<div style='text-align:right; flex:1;'>"
        card_html += f"<div style='font-weight:700; font-size:1.1rem;'>{ach['name']}</div>"
        card_html += f"<div style='color:{theme['muted']}; font-size:0.9rem; margin-top:4px;'>{ach['desc']}</div>"
        card_html += "</div></div>"
        card_html += f"<div style='display:flex; justify-content:space-between; align-items:center; margin-top:16px; gap:8px; flex-wrap:wrap;'>"
        card_html += f"<span class='reward-tag' style='color:{rarity_color}; border: 1px solid {rarity_color};'>⭐ {ach['rarity']}</span>"
        card_html += f"<span class='reward-tag'>+{ach['xp']} XP</span>"
        card_html += f"<span style='color:{status_color}; font-weight:700;'>{status}</span>"
        card_html += "</div></div>"
        grid_items_html.append(card_html)
    
    grid_html = f"<div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 18px;'>{''.join(grid_items_html)}</div>"
    st.markdown(grid_html, unsafe_allow_html=True)


def render_analytics(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title'>Performance Lab</div><div class='section-subtitle'>Track how hydration, streaks, and habits evolve over time.</div>", unsafe_allow_html=True)
    goal = st.session_state.data["profile"].get("custom_goal") or st.session_state.data["profile"].get("goal", 2600)
    weekly = get_weekly_totals(st.session_state.data.get("entries", []), goal)
    intake_history = [total for _, total in weekly]
    chart_data = pd.DataFrame([
        {"day": day, "intake": total, "completion": min(100, int(total / max(1, goal) * 100))}
        for day, total in weekly
    ])
    streak = st.session_state.data["stats"].get("streak", 0)
    best_day = max(intake_history) if intake_history else 0
    avg_intake = int(sum(intake_history) / len(intake_history)) if intake_history else 0
    goal_pct = int(sum(intake_history) / max(1, len(intake_history)) / goal * 100) if intake_history else 0
    cards_html = f"""
      <div class='glass-panel-alt' style='display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px;'>
        <div class='stat-chip'><div class='stat-chip-title'>Average Intake</div><div class='stat-chip-value'>{avg_intake:,} ml</div></div>
        <div class='stat-chip'><div class='stat-chip-title'>Goal Completion</div><div class='stat-chip-value'>{goal_pct}%</div></div>
        <div class='stat-chip'><div class='stat-chip-title'>Best Day</div><div class='stat-chip-value'>{best_day:,} ml</div></div>
        <div class='stat-chip'><div class='stat-chip-title'>Streak</div><div class='stat-chip-value'>{streak} days</div></div>
      </div>
    """
    st.markdown(cards_html, unsafe_allow_html=True)
    if intake_history:
        st.markdown("<div style='margin-top:22px;' class='mini-chart-card'><div style='font-weight:700; margin-bottom:12px;'>7-Day Hydration Trend</div></div>", unsafe_allow_html=True)
        st.altair_chart(
            alt.Chart(chart_data)
            .mark_line(point=True)
            .encode(x=alt.X('day:N', title='Day'), y=alt.Y('intake:Q', title='Intake (ml)'), tooltip=['day:N', 'intake:Q'])
            .properties(height=280),
            use_container_width=True,
        )
        st.markdown("<div style='margin-top:18px;' class='mini-chart-card'><div style='font-weight:700; margin-bottom:12px;'>Goal Completion</div></div>", unsafe_allow_html=True)
        st.altair_chart(
            alt.Chart(chart_data)
            .mark_line(point=True, color=theme['accent'])
            .encode(x=alt.X('day:N', title='Day'), y=alt.Y('completion:Q', title='Completion (%)'), tooltip=['day:N', 'completion:Q'])
            .properties(height=250),
            use_container_width=True,
        )
        st.markdown("<div style='margin-top:18px;' class='mini-chart-card'><div style='font-weight:700; margin-bottom:12px;'>Weekly Summary</div></div>", unsafe_allow_html=True)
        st.altair_chart(
            alt.Chart(chart_data)
            .mark_bar(color=theme['accent_soft'])
            .encode(x=alt.X('day:N', title='Day'), y=alt.Y('intake:Q', title='Intake (ml)'), tooltip=['day:N', 'intake:Q'])
            .properties(height=280),
            use_container_width=True,
        )
    else:
        st.markdown("<div class='glass-panel-alt'>No hydration history yet — log some drinks to see analytics.</div>", unsafe_allow_html=True)


def render_calendar(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title'>Hydration Calendar</div><div class='section-subtitle'>See how every day stacks against your goal.</div>", unsafe_allow_html=True)
    goal = get_active_goal()
    month = get_monthly_calendar(st.session_state.data.get("entries", []), date.today().year, date.today().month, goal)
    cells = []
    for week in month:
        for day in week:
            intensity = day["progress"]
            status_class = "inactive" if not day["is_current_month"] else ""
            fill_color = f"rgba(56,209,246,{0.65 + intensity * 0.0035})"
            
            # Build tile HTML without multi-line f-strings
            tile_html = f"<div class='calendar-cell {status_class}' style='background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.10);'>"
            tile_html += f"<div style='font-size:0.95rem; color: {theme['muted']};'>{day['date'].day}</div>"
            tile_html += f"<div style='font-size:1.5rem; font-weight:700; margin-top:12px; color: {theme['text']};'>{day['progress']}%</div>"
            tile_html += f"<div style='margin-top:10px; width:100%; height:10px; border-radius:999px; background: rgba(255,255,255,0.10);'>"
            tile_html += f"<div style='width:{day['progress']}%; height:100%; border-radius:999px; background: linear-gradient(90deg, {fill_color}, {theme['accent']});'></div>"
            tile_html += "</div></div>"
            cells.append(tile_html)
    
    grid_html = f"<div class='calendar-grid'>{''.join(cells)}</div>"
    st.markdown(grid_html, unsafe_allow_html=True)
    st.markdown("<div style='margin-top:18px;' class='glass-panel-alt'><div style='font-weight:700;'>Tap any day to see details (future feature)</div><div style='color: rgba(255,255,255,0.75); margin-top:8px;'>Hydration tiles show at-a-glance completion strength.</div></div>", unsafe_allow_html=True)


def render_reminders(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title'>Daily Reminders</div><div class='section-subtitle'>Set one practical rolling reminder. After you log a drink, the next alert waits for your chosen gap.</div>", unsafe_allow_html=True)
    settings = st.session_state.data["settings"]
    interval = int(settings.get("reminder_interval_minutes", 60))
    amount = int(settings.get("reminder_amount_ml", 250))
    due, message, next_message = get_hydration_reminder()
    if due:
        st.warning(f"💧 {message}")
    else:
        st.info(f"💧 {next_message}")
    st.markdown(f"<div class='glass-panel-alt'><div style='font-weight:700;'>Current plan</div><div style='color:{theme['muted']}; margin-top:8px;'>Remind every {interval} minutes to drink about {amount} ml. Smaller, regular drinks are more practical than trying to catch up all at once.</div></div>", unsafe_allow_html=True)
    if st.button(f"Log {amount} ml now", key="reminder_page_add"):
        add_entry(amount, "water", "Reminder")
        st.rerun()
    st.markdown("<div class='section-title' style='margin-top:24px;'>Hydration Tips</div>", unsafe_allow_html=True)
    for tip in HYDRATION_TIPS:
        st.markdown(f"<div class='glass-panel-alt' style='margin-bottom:12px;'>💧 {tip}</div>", unsafe_allow_html=True)


def render_insights(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title'>Smart Insights</div><div class='section-subtitle'>Personalized suggestions based on your actual hydration behavior.</div>", unsafe_allow_html=True)
    insights = generate_insights(st.session_state.data)
    if not insights:
        st.markdown("<div class='glass-panel-alt'>No insights available yet — log a few more drinks to activate smarter guidance.</div>", unsafe_allow_html=True)
        return
    cards = []
    for item in insights[:4]:
        card_html = "<div class='glass-panel-alt'>"
        card_html += f"<div style='font-weight:700; margin-bottom:12px;'>🔹 {item['title']}</div>"
        card_html += f"<div style='color: {theme['text']};'>{item['text']}</div>"
        card_html += "</div>"
        cards.append(card_html)
    grid_html = "<div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 16px;'>" + "".join(cards) + "</div>"
    st.markdown(grid_html, unsafe_allow_html=True)


def render_verify(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title'>Verify Your Bottle</div><div class='section-subtitle'>A guided workflow that helps you confirm quantity before logging.</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload or capture a container image", type=["png", "jpg", "jpeg", "bmp"])
    if uploaded is not None:
        st.image(uploaded, use_container_width=True)
        if st.button("Analyze container", key="analyze_image"):
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    temp_file.write(uploaded.getbuffer())
                    temp_file_path = temp_file.name
                result = get_vision_analyzer().analyze_image(temp_file_path)
                st.session_state.verify_result = result
                st.session_state.verify_path = temp_file_path
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                st.session_state.verify_path = None
    if st.session_state.verify_result:
        result = st.session_state.verify_result
        if result.get("error"):
            st.error(result["error"])
        else:
            info_html = f"""
              <div class='glass-panel-alt'>
                <div style='display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap;'>
                  <div><div style='font-weight:700;'>{result.get('container_type', 'Bottle detected')}</div><div style='color: {theme['muted']}; margin-top:6px;'>Capacity estimate</div><div style='font-size:1.9rem; font-weight:700;'>{result.get('estimated_capacity_ml', 'N/A')} ml</div></div>
                  <div><div style='font-weight:700;'>Fill level</div><div style='color: {theme['muted']}; margin-top:6px;'>{result.get('estimated_fill_pct', 0)}%</div></div>
                  <div><div style='font-weight:700;'>Liquid volume</div><div style='color: {theme['muted']}; margin-top:6px;'>{result.get('estimated_volume_ml', 'N/A')} ml</div></div>
                </div>
                <div style='margin-top:16px; display:flex; gap: 12px; flex-wrap:wrap;'><span class='reward-tag'>Confidence: {result.get('confidence', 0)}%</span><span class='reward-tag'>Verify result</span></div>
              </div>
            """
            st.markdown(info_html, unsafe_allow_html=True)
            if st.button("Log estimated hydration", key="log_verified"):
                volume = int(result.get('estimated_volume_ml', 0) or 0)
                if volume > 0:
                    add_entry(volume, "water", "Verified container log")
                    st.session_state.verify_result = None
                    st.success(f"Logged {volume} ml from verified container.")
                else:
                    st.warning("Unable to log unknown volume.")


def render_voice_input(theme: dict[str, str]) -> str | None:
    """Show the current voice-note prototype; expanded support is future work."""
    html = f'''
      <div style="padding:18px; border-radius:24px; background: rgba(255,255,255,0.08); color: {theme['text']}; animation: slideInLeft 0.5s ease both;">
        <div style="font-weight:700; margin-bottom:12px;">🎤 Voice Notes (Future Enhancement)</div>
        <div style="margin-bottom:14px; color: {theme['muted']};font-size:0.9rem;">Expanded voice input and voice-powered logging will be added in a later update. Type in the Notes field below for now.</div>
        <button id="recordButton" style="display:inline-flex; align-items:center; gap:8px; border:none; background: rgba(56,209,246,0.18); color: {theme['text']}; padding: 12px 18px; border-radius: 16px; cursor:pointer; font-weight:700; border: 1px solid rgba(56,209,246,0.3); transition: all 0.3s ease;" onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 8px 20px rgba(56,209,246,0.2)';" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='none';">🎤 Record Note</button>
        <div id="voiceStatus" style="margin-top:12px; color: {theme['muted']};font-size:0.9rem;">Ready to record.</div>
      </div>
    '''
    script = '''
      <script>
        const recordButton = document.getElementById('recordButton');
        const status = document.getElementById('voiceStatus');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
          status.textContent = '🔔 Voice input not supported in this browser. Use the Notes field below to type instead.';
          recordButton.disabled = true;
          recordButton.style.opacity = '0.5';
        } else {
          const recognition = new SpeechRecognition();
          recognition.lang = 'en-US';
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;

          recordButton.addEventListener('click', (e) => {
            e.preventDefault();
            recognition.start();
            status.textContent = '🎧 Listening... speak now...';
            recordButton.textContent = '🎙️ Listening...';
            recordButton.disabled = true;
          });

          recognition.addEventListener('result', (event) => {
            if (!event.results || !event.results[0]) return;
            const transcript = event.results[0][0].transcript.trim();
            if (transcript) {
              status.textContent = '✓ Voice captured! Copy the text below and paste into Notes.';
              const notesField = document.querySelector('textarea[aria-label="Notes"]') || document.querySelector('textarea');
              if (notesField) {
                notesField.value = (notesField.value ? notesField.value + ' ' : '') + transcript;
                notesField.focus();
              }
            }
            recordButton.textContent = '🎤 Record Note';
            recordButton.disabled = false;
          });

          recognition.addEventListener('error', (event) => {
            status.textContent = `⚠️ Error: ${event.error}. Try again.`;
            recordButton.textContent = '🎤 Record Note';
            recordButton.disabled = false;
          });

          recognition.addEventListener('end', () => {
            recordButton.textContent = '🎤 Record Note';
            recordButton.disabled = false;
          });
        }
      </script>
    '''
    try:
        components.html(html + script, height=140, scrolling=False)
    except Exception as e:
        st.warning(f"Voice component unavailable: {str(e)[:50]}. Use the Notes field below.")
    return None


def render_shop(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title'>Buddy Customization Shop</div><div class='section-subtitle'>Earn diamonds by logging drinks and completing hydration quests.</div>", unsafe_allow_html=True)
    buddy = st.session_state.data.setdefault("buddy", {})
    shop = st.session_state.data.setdefault("shop", {})
    owned_items = shop.setdefault("owned", ["default"])
    equipped = shop.setdefault("equipped", [])
    skin = shop.setdefault("skin", "classic")
    coins = st.session_state.data["stats"].get("coins", 0)
    st.markdown(f"<div class='glass-panel-alt'><div style='font-weight:700;'>Diamond Wallet</div><div style='margin-top:8px; color:{theme['muted']};'>You have {coins} diamonds.</div></div>", unsafe_allow_html=True)

    with st.form("buddy_name_form"):
        buddy_name = st.text_input(
            "Buddy name",
            value=buddy.get("name", "Buddy"),
            max_chars=32,
            help="Choose a name for your hydration companion.",
        )
        if st.form_submit_button("Save Buddy name", use_container_width=True):
            buddy["name"] = buddy_name.strip() or "Buddy"
            save_data_state("Buddy name updated.")
            st.rerun()

    st.markdown("<div class='section-title' style='font-size:1.3rem; margin-top:24px;'>Shop</div>", unsafe_allow_html=True)
    item_columns = st.columns(3)
    for item in REWARD_ITEMS:
        owned = item["id"] in owned_items
        active = skin == item["id"] if item["category"] == "Skin" else item["id"] in equipped
        wearable = is_cosmetic_wearable(item["id"])
        with item_columns[REWARD_ITEMS.index(item) % 3]:
            st.markdown(
                f"<div class='achievement-card'><div style='display:flex; justify-content:space-between; gap:12px;'><strong>{item['name']}</strong><strong style='color:{theme['accent']};'>{item['cost']} 💎</strong></div><div style='color:{theme['muted']}; margin-top:6px;'>{item['category']} • {item['rarity']}</div><div style='margin-top:10px; color:{theme['accent']};'>{'✓ Wearable on Buddy' if wearable else 'Unavailable'}</div></div>",
                unsafe_allow_html=True,
            )
            if not owned:
                if st.button(f"Buy for {item['cost']} 💎", key=f"buy_{item['id']}", use_container_width=True, disabled=coins < item["cost"]):
                    st.session_state.data["stats"]["coins"] = coins - item["cost"]
                    owned_items.append(item["id"])
                    shop["owned"] = owned_items
                    if item["category"] == "Skin":
                        shop["skin"] = item["id"]
                    elif item["id"] not in equipped:
                        equipped.append(item["id"])
                        shop["equipped"] = equipped
                    save_data_state(f"Purchased {item['name']}.")
                    st.rerun()
            elif active:
                if st.button("Owned • Unequip", key=f"unequip_{item['id']}", use_container_width=True):
                    shop = toggle_equipment_state(shop, item["id"], item["category"], False)
                    st.session_state.data["shop"] = shop
                    save_data_state(f"Unequipped {item['name']}.")
                    st.rerun()
            else:
                if st.button("Owned • Equip", key=f"equip_{item['id']}", use_container_width=True):
                    shop = toggle_equipment_state(shop, item["id"], item["category"], True)
                    st.session_state.data["shop"] = shop
                    save_data_state(f"Equipped {item['name']}.")
                    st.rerun()

    st.markdown("<div class='section-title' style='font-size:1.3rem; margin-top:28px;'>Your Vault</div><div class='section-subtitle'>Everything you own is saved here.</div>", unsafe_allow_html=True)
    vault_items = [item for item in REWARD_ITEMS if item["id"] in owned_items]
    if not vault_items:
        st.info("Your Vault is empty. Buy an item to save it here.")
    else:
        vault_columns = st.columns(3)
        for item in vault_items:
            active = skin == item["id"] if item["category"] == "Skin" else item["id"] in equipped
            with vault_columns[vault_items.index(item) % 3]:
                st.markdown(f"<div class='glass-panel-alt'><strong>{item['name']}</strong><div style='color:{theme['muted']}; margin-top:6px;'>{item['rarity']} • Saved forever</div></div>", unsafe_allow_html=True)
                if active:
                    if st.button("Equipped • Unequip", key=f"vault_unequip_{item['id']}", use_container_width=True):
                        shop = toggle_equipment_state(shop, item["id"], item["category"], False)
                        st.session_state.data["shop"] = shop
                        save_data_state(f"Unequipped {item['name']} from Your Vault.")
                        st.rerun()
                else:
                    if st.button("Equip from Vault", key=f"vault_equip_{item['id']}", use_container_width=True):
                        shop = toggle_equipment_state(shop, item["id"], item["category"], True)
                        st.session_state.data["shop"] = shop
                        save_data_state(f"Equipped {item['name']} from Your Vault.")
                        st.rerun()


def render_buddy(theme: dict[str, str]) -> None:
    apply_buddy_mood()
    buddy = get_buddy_state()
    st.markdown(f"<div class='section-title' style='animation: slideInLeft 0.5s ease both;'>🐣 Buddy Lounge</div><div class='section-subtitle'>Your virtual friend grows as you hydrate.</div>", unsafe_allow_html=True)
    buddy_panel = f"""
      <div class='glass-panel' style='animation: slideInRight 0.6s ease 0.1s both;'>
        <div style='display:flex; gap:24px; flex-wrap:wrap; align-items:center; justify-content:space-between;'>
          <div style='display:grid; gap:18px;'>
            <div style='font-size:4.2rem; animation: bounce 1.6s ease-in-out infinite;'>💧</div>
            <div style='font-weight:700; font-size:1.45rem;'>✨ {buddy['name']}</div>
            <div style='font-size:1.1rem; color:{theme['muted']};'>Mood: {buddy['expression'].title()} • {buddy.get('status_message', 'Keep sipping!')}</div>
          </div>
          <div style='display:grid; gap:12px; min-width:220px;'>
            {get_buddy_avatar_html(buddy, theme, get_today_progress_percent())}
          </div>
        </div>
      </div>
    """
    st.markdown(buddy_panel, unsafe_allow_html=True)
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    action_cols = st.columns(3)
    if action_cols[0].button('💬 Talk to Buddy', key='buddy_talk', use_container_width=True):
        st.info("Gemini-powered HydroCoach chat is a future enhancement and will be added in a later update.")
    if action_cols[1].button('🎨 Customize', key='buddy_customize_btn', use_container_width=True):
        st.info('💡 Scroll down to customize your buddy!')
    if action_cols[2].button('🎁 Open Shop', key='buddy_shop_btn', use_container_width=True):
        st.info('🛍️ Shop coming up below!')
    status_html = f"""
      <div class='glass-panel-alt' style='margin-top:18px; animation: slideInLeft 0.6s ease 0.2s both;'>
        <div style='font-weight:700; margin-bottom:12px;'>📊 Buddy Status</div>
        <div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;'>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.1s both;'>💧 Water Drop Buddy</div>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.2s both;'>⚡ Energy: {get_today_progress_percent()}%</div>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.3s both;'>⭐ XP: {st.session_state.data['stats'].get('points', 0)}</div>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.4s both;'>😊 {buddy['expression']}</div>
        </div>
      </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.info("Your water-drop Buddy smiles when you reach your goal, looks hopeful as you progress, and cries when you need a sip.")
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    render_shop(theme)


def render_log(theme: dict[str, str]) -> None:
    st.markdown(f"<div class='section-title' style='color:{theme['accent']};'>💧 Hydration Lab</div><div class='section-subtitle'>Log drinks faster, track streaks, and power up your buddy.</div>", unsafe_allow_html=True)
    if "voice_log" not in st.session_state:
        st.session_state["voice_log"] = ""
    with st.form("log_form"):
        amount = st.number_input("Amount (ml)", min_value=10, max_value=3000, value=int(250), step=10, format="%d")
        drink = st.selectbox("Drink type", DRINK_TYPES + st.session_state.data["profile"].get("custom_drink_types", []))
        st.markdown(f"<div style='margin-bottom: 16px; font-size: 0.95rem; color: {theme['muted']};'>💡 Tip: Use voice notes or type custom notes for tracking mood, time, or context.</div>", unsafe_allow_html=True)
        render_voice_input(theme)
        notes = st.text_area("Notes", value=st.session_state.get("voice_log", ""), key="notes_input", height=140, placeholder="Add any notes about this drink...")
        submitted = st.form_submit_button("✓ Log Drink", use_container_width=True)
        if submitted:
            add_entry(int(amount), drink, notes)
            query_page("Home")
            st.rerun()
    st.markdown("<div style='margin-top:24px;'><span class='section-title'>⚡ Quick Add</span></div>", unsafe_allow_html=True)
    control_cols = st.columns(2)
    with control_cols[0]:
        if st.button("↩ Undo Last Log", key="undo_last_log", use_container_width=True, disabled=not st.session_state.data.get("entries")):
            undo_last_entry()
            st.rerun()
    with control_cols[1]:
        if st.button("🧹 Reset Hydration Logs", key="reset_hydration_logs_log", use_container_width=True, disabled=not st.session_state.data.get("entries")):
            reset_hydration_logs()
            st.rerun()
    quick_cols = st.columns([1,1,1,1,1])
    quick_amounts = [100, 250, 330, 500, 750]
    for idx, value in enumerate(quick_amounts):
        with quick_cols[idx]:
            btn_html = f"""
                <div style='
                    animation: popIn 0.6s ease both;
                    animation-delay: {idx * 0.1}s;
                '>
                    <button style='
                        width: 100%;
                        padding: 16px 8px;
                        border-radius: 18px;
                        border: 1px solid rgba(56,209,246,0.3);
                        background: rgba(56,209,246,0.12);
                        color: {theme['text']};
                        font-weight: 700;
                        cursor: pointer;
                        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
                        font-size: 1rem;
                    ' onmouseover="this.style.transform='scale(1.08) translateY(-4px)'; this.style.boxShadow='0 12px 30px rgba(56,209,246,0.2)';" 
                       onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='none';">
                        +{value} ml
                    </button>
                </div>
            """
            if st.button(f"+{value} ml", key=f"quick_add_{value}", use_container_width=True):
                add_entry(value, "water", "Quick add")
                query_page("Home")
    
    st.markdown("<div style='margin-top:20px;' class='glass-panel-alt'><div style='font-weight:700; margin-bottom:12px;'>📝 Custom Drink Types</div>", unsafe_allow_html=True)
    custom_drinks = st.session_state.data["profile"].get("custom_drink_types", [])
    if custom_drinks:
        st.write(", ".join(custom_drinks))
    else:
        st.markdown(f"<div style='color:{theme['muted']};'>No custom drinks yet. Edit in Settings to add your favorites.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_settings(theme: dict[str, str]) -> None:
    st.markdown("<div class='section-title'>Settings</div><div class='section-subtitle'>Tweak the look, backup data, and manage your hydration preferences.</div>", unsafe_allow_html=True)
    profile = st.session_state.data["profile"]
    with st.container():
        st.markdown("<div class='glass-panel'><div style='font-weight:700; margin-bottom:14px;'>Profile & Hydration Preferences</div></div>", unsafe_allow_html=True)
        cols = st.columns(2)
        with cols[0]:
            name = st.text_input("Your name", value=profile.get("name", ""), placeholder="Enter your name")
            gender_options = ["Female", "Male", "Non-binary", "Prefer not to say"]
            current_gender = profile.get("gender", "Prefer not to say")
            gender = st.selectbox("Gender", gender_options, index=gender_options.index(current_gender) if current_gender in gender_options else gender_options.index("Prefer not to say"))
            age = st.number_input("Age", min_value=5, max_value=120, value=int(profile.get("age", 25) or 25), step=1)
            weight = st.number_input("Weight (kg)", min_value=30, max_value=200, value=int(profile.get("weight", 70) or 70), step=1)
            activity = st.selectbox("Activity level", ["low", "moderate", "high", "very_high"], index=["low", "moderate", "high", "very_high"].index(profile.get("activity", "moderate")))
        with cols[1]:
            occupations = get_all_occupations()
            current_occ = profile.get("occupation", "Student")
            occ_index = occupations.index(current_occ) if current_occ in occupations else occupations.index("Student")
            occupation = st.selectbox("Occupation", occupations, index=occ_index, help="Select your occupation for tailored hydration recommendations")
            climate = st.selectbox("Climate", ["cool", "warm", "hot"], index=["cool", "warm", "hot"].index(profile.get("climate", "warm")))
            custom_goal = st.number_input("Custom daily goal (ml)", min_value=0, max_value=5000, value=int(profile.get("custom_goal") or 0), step=50, help="Leave 0 to use the calculated goal.")
            if custom_goal == 0:
                custom_goal = None
        
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        
        def apply_recommendation_goal(recommendation_ml: int, label: str) -> None:
            profile["custom_goal"] = recommendation_ml
            profile["goal"] = recommendation_ml
            save_data_state(f"{label} added as your daily goal.")
            st.rerun()

        # Display recommendations based on the three profile factors.
        st.markdown(f"<div style='font-weight:700; margin-bottom:12px; font-size:1.1rem;'>📊 Personalized Recommendations</div>", unsafe_allow_html=True)

        age_rec = get_age_recommendation(age)
        occ_rec = get_occupation_recommendation(occupation)
        climate_rec = get_climate_recommendation(climate)
        recommendation_cards = [
            ("age", f"👤 Age Group ({age_rec['age_range']})", age_rec["recommended_ml"], f"≈ {age_rec['cups_per_day']} cups per day", age_rec["hydration_tips"]),
            ("occupation", f"{occ_rec['icon']} {occupation}", occ_rec["recommended_ml"], occ_rec["note"], occ_rec["tips"]),
            ("climate", f"🌡️ {climate.title()} Climate", climate_rec["recommended_ml"], climate_rec["note"], climate_rec["tips"]),
        ]

        rec_cols = st.columns(3)
        for column, (key, title, recommended_ml, detail, tip) in zip(rec_cols, recommendation_cards):
            with column:
                st.markdown(
                    f"<div class='glass-panel-alt' style='min-height:250px;'><div style='font-weight:700; margin-bottom:8px;'>{title}</div>"
                    f"<div style='font-size:1.3rem; font-weight:700; color:{theme['accent']}; margin-bottom:8px;'>{recommended_ml} ml/day</div>"
                    f"<div style='color:{theme['muted']}; font-size:0.85rem; margin-bottom:8px;'>{detail}</div>"
                    f"<div style='margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1); font-size:0.85rem;'><strong>💡 Tip:</strong> {tip}</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button("Add to goals", key=f"add_{key}_recommendation", use_container_width=True):
                    apply_recommendation_goal(recommended_ml, f"{title} recommendation")
        
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        goal_preview = custom_goal or calculate_hydration_goal(age, weight, activity, climate, occupation)
        average_recommendation = round(sum(card[2] for card in recommendation_cards) / len(recommendation_cards))
        st.markdown(f"<div class='glass-panel-alt'><div style='font-weight:700;'>🎯 Final Recommendation</div><div style='font-size:1.5rem; font-weight:800; color:{theme['accent']}; margin-top:10px;'>{average_recommendation:,} ml/day</div><div style='color:{theme['muted']}; margin-top:6px;'>Average of your age, occupation, and climate recommendations.</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='glass-panel-alt'><div style='font-weight:700;'>🎯 Your Personalized Goal</div><div style='margin-top:12px; display:grid; grid-template-columns:repeat(4, 1fr); gap:12px;'><div><div style='color:{theme['muted']}; font-size:0.85rem;'>Calculated Target</div><div style='font-size:1.4rem; font-weight:800; color:{theme['accent']};'>{goal_preview:,} ml</div></div><div><div style='color:{theme['muted']}; font-size:0.85rem;'>Age</div><div style='font-size:1.1rem; font-weight:700;'>{age_rec['recommended_ml']} ml</div></div><div><div style='color:{theme['muted']}; font-size:0.85rem;'>Occupation</div><div style='font-size:1.1rem; font-weight:700;'>{occ_rec['recommended_ml']} ml</div></div><div><div style='color:{theme['muted']}; font-size:0.85rem;'>Climate</div><div style='font-size:1.1rem; font-weight:700;'>{climate_rec['recommended_ml']} ml</div></div></div></div>", unsafe_allow_html=True)
        if st.button("Add final recommendation to goals", key="add_final_recommendation", use_container_width=True):
            apply_recommendation_goal(average_recommendation, "Final recommendation")
        
        theme_choice = st.selectbox("Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.data["settings"].get("theme", "ocean")))
        
        # Day/Night Mode Toggle
        st.markdown(f"<div style='margin-top:20px; margin-bottom:12px;'><label class='settings-label' style='color:{theme['accent']};'>QUICK ACTIONS</label></div>", unsafe_allow_html=True)
        mode_cols = st.columns([1, 1, 1])
        with mode_cols[0]:
            if st.button("🌙 Night Mode", key="quick_night_settings", use_container_width=True):
                theme_choice = "ocean"
                st.session_state.data["settings"]["theme"] = "ocean"
                st.rerun()
        with mode_cols[1]:
            if st.button("☀️ Day Mode", key="quick_day_settings", use_container_width=True):
                theme_choice = "day"
                st.session_state.data["settings"]["theme"] = "day"
                st.rerun()
        with mode_cols[2]:
            render_reset_all_action("🔄 Reset Data", "reset_settings", "✅ All data reset!", "Settings")
        
        notifications = st.checkbox("Enable notifications", value=st.session_state.data["settings"].get("notifications", True))
        auto_save = st.checkbox("Auto save changes", value=st.session_state.data["settings"].get("auto_save", True))
        reminder_interval = st.number_input("Reminder gap (minutes)", min_value=15, max_value=240, value=int(st.session_state.data["settings"].get("reminder_interval_minutes", 60)), step=15)
        reminder_amount = st.number_input("Reminder amount (ml)", min_value=50, max_value=1000, value=int(st.session_state.data["settings"].get("reminder_amount_ml", 250)), step=50)
        if st.button("Save settings", key="save_settings"):
            profile["name"] = name.strip()
            profile["gender"] = gender
            profile["age"] = age
            profile["occupation"] = occupation
            profile["weight"] = weight
            profile["activity"] = activity
            profile["climate"] = climate
            profile["custom_goal"] = custom_goal
            if custom_goal is None:
                profile["goal"] = calculate_hydration_goal(
                    age,
                    weight,
                    activity,
                    climate,
                    occupation,
                )
            st.session_state.data["settings"]["theme"] = theme_choice
            st.session_state.data["settings"]["notifications"] = notifications
            st.session_state.data["settings"]["auto_save"] = auto_save
            st.session_state.data["settings"]["reminder_interval_minutes"] = int(reminder_interval)
            st.session_state.data["settings"]["reminder_amount_ml"] = int(reminder_amount)
            save_data_state("Settings updated.")
            query_page("Settings")
    reset_cols = st.columns(2)
    with reset_cols[0]:
        if st.button("Reset hydration logs only", key="reset_hydration"):
            reset_hydration_logs()
            st.rerun()
    with reset_cols[1]:
        render_reset_all_action("Reset everything", "reset_everything", "All progress reset.", "Settings")
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='glass-panel-alt'><div style='font-weight:700; margin-bottom:14px;'>Data & Backup</div></div>", unsafe_allow_html=True)
        if st.button("Export data as JSON"):
            payload = json.dumps(st.session_state.data, indent=2)
            st.download_button("Download backup", payload, file_name="water_buddy_backup.json", mime="application/json")
        uploaded = st.file_uploader("Import backup", type=["json"], key="import_backup")
        if uploaded is not None and st.button("Import backup file", key="import_backup_button"):
            try:
                imported = json.load(uploaded)
                if not isinstance(imported, dict) or "profile" not in imported:
                    st.error("Invalid backup format.")
                else:
                    st.session_state.data = imported
                    save_data_state("Backup imported.")
                    query_page("Settings")
                    st.rerun()
            except Exception as exc:
                st.error(f"Import failed: {exc}")
        if st.button("Reset all progress", key="reset_data"):
            st.session_state["confirm_reset_data"] = True
            st.rerun()
        if st.session_state.get("confirm_reset_data", False):
            st.warning("Are you sure you want to clear all data? You will lose your hydration progress, streaks, coins, Buddy items, and settings.")
            confirm_cols = st.columns(2)
            with confirm_cols[0]:
                if st.button("Yes, clear all data", key="reset_data_confirm", use_container_width=True):
                    reset_all_data("Reset complete.")
                    st.session_state.pop("confirm_reset_data", None)
                    query_page("Settings")
                    st.rerun()
            with confirm_cols[1]:
                if st.button("Cancel", key="reset_data_cancel", use_container_width=True):
                    st.session_state.pop("confirm_reset_data", None)
                    st.rerun()


def render_page(page: str, theme: dict[str, str]) -> None:
    if page == "Home":
        render_home(theme)
    elif page == "Hydrate":
        render_log(theme)
    elif page == "Verify":
        render_verify(theme)
    elif page == "Buddy":
        render_buddy(theme)
    elif page == "Quests":
        render_quests(theme)
    elif page == "Achievements":
        render_achievements(theme)
    elif page == "Analytics":
        render_analytics(theme)
    elif page == "Insights":
        render_insights(theme)
    elif page == "Calendar":
        render_calendar(theme)
    elif page == "Reminders":
        render_reminders(theme)
    elif page == "Settings":
        render_settings(theme)
    else:
        render_home(theme)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="💧", layout="wide", initial_sidebar_state="expanded")
    if not render_authentication():
        return
    init_state()
    refresh_for_new_day()
    schedule_midnight_refresh()
    theme_name = st.session_state.data["settings"].get("theme", "ocean")
    theme = style_page(theme_name)
    render_water_drop_celebration()
    if not st.session_state.data["profile"].get("onboarding_complete", False):
        render_onboarding(theme)
        return
    page = get_current_page()

    render_left_settings_panel(page, theme)
    render_toast()
    render_welcome_header(theme)
    render_page(page, theme)

    if st.session_state.data.get("settings", {}).get("auto_save", True):
        save_data(st.session_state.data, st.session_state["username"])

if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        print("Start Water Buddy with: streamlit run waterbuddy.py")
