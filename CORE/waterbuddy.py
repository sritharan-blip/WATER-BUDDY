import copy
import json
import os
import tempfile
from datetime import date, datetime
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import quote

from core.analytics import get_monthly_calendar, get_weekly_totals
from core.achievements import ACHIEVEMENT_DEFINITIONS, evaluate_achievements
from core.hydration import (DRINK_TYPES, calculate_hydration_goal,
                            calculate_streak, get_level_info,
                            get_progress_percent, get_motivation,
                            get_age_recommendation, get_occupation_recommendation,
                            get_climate_recommendation, get_all_occupations,
                            parse_drink_text)
from core.insights import generate_insights
from core.storage import DEFAULT_DATA, load_data, save_data
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
    {"id": "Settings", "label": "Settings", "icon": "⚙️"},
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
    {"id": "galaxy_background", "name": "Galaxy Buddy", "cost": 500, "category": "Background", "rarity": "LEGENDARY"},
    {"id": "crown_hat", "name": "Royal Crown", "cost": 240, "category": "Accessories", "rarity": "EPIC"},
    {"id": "neon_glasses", "name": "Neon Shades", "cost": 120, "category": "Accessories", "rarity": "RARE"},
    {"id": "rainbow_glow", "name": "Aura Glow", "cost": 320, "category": "Effects", "rarity": "EPIC"},
]

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


def get_buddy_avatar_html(buddy: dict[str, Any], theme: dict[str, str], progress_percent: int = 0) -> str:
    species = buddy.get("species", "duckling")
    custom_emoji = buddy.get("custom_emoji", "")
    accessories = buddy.get("accessories", [])
    accessory = accessories[0] if accessories and len(accessories) > 0 else None
    environment = buddy.get("environment", "ocean")
    emoji = custom_emoji.strip() or theme.get("mascot", BUDDY_SPECIES_ART.get(species, "🐣"))
    expression = get_buddy_expression(progress_percent)
    expression_icon = BUDDY_EXPRESSIONS[expression]
    mascot_name = theme.get("mascot_name", species.title())
    accessory_icon = BUDDY_ACCESSORY_LABELS.get(accessory, "")
    bg1, bg2 = BUDDY_ENV_BACKGROUNDS.get(environment, ("#0b2134", "#0b3f5d"))
    svg = f'''
      <svg width="260" height="260" viewBox="0 0 260 260" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="buddyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{bg1}"/>
            <stop offset="100%" stop-color="{bg2}"/>
          </linearGradient>
          <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
            <feDropShadow dx="0" dy="0" stdDeviation="18" flood-color="{theme['accent']}" flood-opacity="0.4"/>
          </filter>
        </defs>
        <rect x="10" y="10" width="240" height="240" rx="40" ry="40" fill="url(#buddyGradient)" filter="url(#glow)" />
        <circle cx="130" cy="100" r="72" fill="#ffffff" fill-opacity="0.08" />
        <text x="50%" y="52%" dominant-baseline="middle" text-anchor="middle" font-size="72" font-family="Segoe UI Emoji, Arial, sans-serif">{emoji}</text>
        <text x="50%" y="78%" dominant-baseline="middle" text-anchor="middle" font-size="24" fill="{theme['text']}" font-family="Segoe UI, Arial, sans-serif">{mascot_name} {expression_icon}</text>
        <text x="50%" y="89%" dominant-baseline="middle" text-anchor="middle" font-size="18" fill="{theme['muted']}" font-family="Segoe UI, Arial, sans-serif">{environment.title()} {accessory_icon}</text>
      </svg>
    '''
    return f'<img class="buddy-avatar-img" src="data:image/svg+xml;charset=utf-8,{quote(svg)}" alt="Buddy avatar" />'


def style_page(theme_name: str) -> dict[str, str]:
    theme = THEMES.get(theme_name, THEMES["ocean"])
    input_bg = theme['surface_alt']
    placeholder_color = 'rgba(13,31,56,0.45)' if theme_name == 'day' else 'rgba(255,255,255,0.65)'
    css = f"""
    <style>
    #MainMenu, header, footer {{ visibility: hidden; }}
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


def _safe_default_config(key: str, fallback: dict[str, Any]) -> dict[str, Any]:
    if isinstance(DEFAULT_DATA, dict):
        value = DEFAULT_DATA.get(key)
        if isinstance(value, dict):
            return value.copy()
    return fallback.copy()


def init_state() -> None:
    if "data" not in st.session_state:
        data = load_data()
        data["profile"].setdefault("name", "")
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


def save_data_state(message: str | None = None) -> None:
    save_data(st.session_state.data)
    evaluate_achievements(st.session_state.data)
    if message:
        st.session_state.toast_message = message


def reset_all_data(message: str = "All progress reset.") -> None:
    """Reset the complete profile and progress so onboarding starts again."""
    st.session_state.data = copy.deepcopy(DEFAULT_DATA)
    st.session_state.data["profile"]["onboarding_complete"] = False
    save_data_state(message)


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
    species = buddy.get("species", "duckling")
    mood = buddy.get("mood", "happy")
    custom_emoji = buddy.get("custom_emoji", "")
    emoji = custom_emoji.strip() or BUDDY_SPECIES_ART.get(species, "🐣")
    expression = get_buddy_expression(get_today_progress_percent())
    buddy_name = buddy.get("name", "Buddy")
    return {"emoji": emoji, "expression": expression, "name": buddy_name, **buddy}


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
    """Render the visible top navigation toggle and interactive menu."""
    if "nav_menu_open" not in st.session_state:
        st.session_state.nav_menu_open = False

    col1, col2 = st.columns([0.8, 9.2])
    with col1:
        if st.button("☰", key="sidebar_toggle_unique", help="Toggle sidebar", use_container_width=True):
            st.session_state.nav_menu_open = not st.session_state.nav_menu_open

    with col2:
        st.markdown(
            f"<div style='font-size: 2rem; font-weight: 700; color: {theme['text']}; padding-left: 12px; margin-top: 2px;'>💧 Water Buddy</div>",
            unsafe_allow_html=True,
        )

    if st.session_state.nav_menu_open:
        st.markdown(f"<div style='margin-top: 10px; margin-bottom: 8px;'></div>", unsafe_allow_html=True)
        st.markdown(f"<label class='settings-label' style='color:{theme['accent']};'>PAGES</label>", unsafe_allow_html=True)
        for item in NAV_ITEMS:
            is_active = item["id"] == active_page
            label = f"{item['icon']} {item['label']}" + (" ✓" if is_active else "")
            if st.button(label, key=f"nav_btn_{item['id']}_v2", use_container_width=True):
                query_page(item["id"])
                st.session_state.nav_menu_open = False
                st.rerun()

        st.divider()
        st.markdown(f"<label class='settings-label' style='color:{theme['accent']};'>QUICK LINKS</label>", unsafe_allow_html=True)
        quick_cols = st.columns(2)
        with quick_cols[0]:
            if st.button("⚙️ Settings", key="nav_settings_menu", use_container_width=True):
                query_page("Settings")
                st.session_state.nav_menu_open = False
                st.rerun()
        with quick_cols[1]:
            if st.button("📊 Analytics", key="nav_analytics_menu", use_container_width=True):
                query_page("Analytics")
                st.session_state.nav_menu_open = False
                st.rerun()


def render_nav(active_page: str, theme: dict[str, str]) -> None:
    """Navigation is now in the left sidebar - this is a placeholder."""
    pass  # Navigation handled in render_left_settings_panel


def render_toast() -> None:
    message = st.session_state.get("toast_message", "")
    if message:
        st.markdown(f"<div class='toast-banner'>💧 {message}</div>", unsafe_allow_html=True)
        st.session_state.toast_message = ""


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
    with st.form("onboarding_form"):
        st.markdown("<div class='glass-panel' style='max-width:760px; margin: 24px auto;'>", unsafe_allow_html=True)
        name = st.text_input("Your name", value=profile.get("name", ""), placeholder="Enter your name")
        cols = st.columns(2)
        with cols[0]:
            age = st.number_input("Age", min_value=5, max_value=120, value=int(profile.get("age", 25) or 25), step=1)
            weight = st.number_input("Weight (kg)", min_value=30, max_value=200, value=int(profile.get("weight", 70) or 70), step=1)
            activity = st.selectbox("Activity level", ["low", "moderate", "high", "very_high"], index=["low", "moderate", "high", "very_high"].index(profile.get("activity", "moderate")))
        with cols[1]:
            occupations = get_all_occupations()
            current_occupation = profile.get("occupation", "Student")
            occupation = st.selectbox("Occupation", occupations, index=occupations.index(current_occupation) if current_occupation in occupations else occupations.index("Student"))
            climate = st.selectbox("Climate", ["cool", "warm", "hot"], index=["cool", "warm", "hot"].index(profile.get("climate", "warm")))
            custom_goal = st.number_input("Custom daily goal (ml)", min_value=0, max_value=5000, value=int(profile.get("custom_goal") or 0), step=50)
        st.markdown("</div>", unsafe_allow_html=True)
        submit_cols = st.columns(2)
        with submit_cols[0]:
            submitted = st.form_submit_button("Start my hydration journey", use_container_width=True)
        with submit_cols[1]:
            skipped = st.form_submit_button("Skip for now", use_container_width=True)

    if submitted or skipped:
        profile["name"] = name.strip()
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
        if st.button("🔄 Reset All Data", key="reset_home", use_container_width=True):
            reset_all_data("✅ All data has been reset!")
            st.rerun()
    
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    
    render_progress_hero(goal, intake, theme)
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
                <div class='buddy-label'>Level {get_level_info(st.session_state.data['stats'].get('points', 0))['level']} • {theme.get('mascot_name', buddy['species'].title())} • {buddy['environment'].title()}</div>
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
    """Simplified voice input with fallback text input."""
    html = f'''
      <div style="padding:18px; border-radius:24px; background: rgba(255,255,255,0.08); color: {theme['text']}; animation: slideInLeft 0.5s ease both;">
        <div style="font-weight:700; margin-bottom:12px;">🎤 Voice Notes (Beta)</div>
        <div style="margin-bottom:14px; color: {theme['muted']};font-size:0.9rem;">Tap record and speak a note. Note: Requires browser support. Fallback to typing in the Notes field below.</div>
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
    st.markdown("<div class='section-title'>Reward Shop</div><div class='section-subtitle'>Spend Aqua Coins on Buddy gear and rare effects.</div>", unsafe_allow_html=True)
    coins = st.session_state.data["stats"].get("coins", 0)
    st.markdown(f"<div class='glass-panel-alt'><div style='font-weight:700;'>Wallet</div><div style='margin-top:8px; color:{theme['muted']};'>You have {coins} Aqua Coins.</div></div>", unsafe_allow_html=True)
    cards = []
    for item in REWARD_ITEMS:
        owned = item["id"] in st.session_state.data["shop"].get("owned", [])
        button_text = "Equipped" if st.session_state.data["shop"].get("selected") == item["id"] else "Owned" if owned else f"Buy {item['cost']}"
        
        # Build shop card HTML using string concatenation
        card_html = "<div class='achievement-card'>"
        card_html += f"<div style='display:flex; justify-content:space-between; align-items:start; gap:18px;'>"
        card_html += f"<div><div style='font-weight:700;'>{item['name']}</div><div style='color:{theme['muted']}; margin-top:6px;'>{item['category']} • {item['rarity']}</div></div>"
        card_html += f"<div style='font-weight:700; color:{theme['accent']};'>{item['cost']} 💎</div></div>"
        card_html += f"<div style='margin-top:16px;'><div class='glass-button' style='cursor:default; opacity:0.85;'>{button_text}</div></div>"
        card_html += "</div>"
        cards.append(card_html)
    
    st.markdown("<div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:16px; margin-top:16px;'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    for item in REWARD_ITEMS:
        if item["id"] not in st.session_state.data["shop"].get("owned", []) and coins >= item["cost"]:
            if st.button(f"Buy {item['name']}", key=f"buy_{item['id']}"):
                st.session_state.data["stats"]["coins"] = coins - item["cost"]
                st.session_state.data["shop"]["owned"].append(item["id"])
                st.session_state.data["shop"]["selected"] = item["id"]
                save_data_state(f"Purchased {item['name']}.")
                query_page("Buddy")
        elif item["id"] in st.session_state.data["shop"]["owned"] and st.session_state.data["shop"].get("selected") != item["id"]:
            if st.button(f"Equip {item['name']}", key=f"equip_{item['id']}"):
                st.session_state.data["shop"]["selected"] = item["id"]
                save_data_state(f"Equipped {item['name']}.")
                query_page("Buddy")


def render_buddy(theme: dict[str, str]) -> None:
    apply_buddy_mood()
    buddy = get_buddy_state()
    st.markdown(f"<div class='section-title' style='animation: slideInLeft 0.5s ease both;'>🐣 Buddy Lounge</div><div class='section-subtitle'>Your virtual friend grows as you hydrate.</div>", unsafe_allow_html=True)
    buddy_panel = f"""
      <div class='glass-panel' style='animation: slideInRight 0.6s ease 0.1s both;'>
        <div style='display:flex; gap:24px; flex-wrap:wrap; align-items:center; justify-content:space-between;'>
          <div style='display:grid; gap:18px;'>
            <div style='font-size:4.2rem; animation: bounce 1.6s ease-in-out infinite;'>{buddy.get('custom_emoji', '').strip() or theme.get('mascot', buddy['emoji'])}</div>
            <div style='font-weight:700; font-size:1.45rem;'>✨ {buddy['name']}</div>
            <div style='font-size:1.1rem; color:{theme['muted']};'>Mood: {buddy['expression'].title()} • {buddy['environment'].title()}</div>
            <div style='color:{theme['muted']};'>{buddy.get('accessories', []) and '🎀 Accessory: ' + ', '.join(buddy['accessories']).title() or '✨ No accessory equipped'}</div>
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
        st.success('🐣 Buddy chirps: Keep sipping, hydration hero! 💧')
    if action_cols[1].button('🎨 Customize', key='buddy_customize_btn', use_container_width=True):
        st.info('💡 Scroll down to customize your buddy!')
    if action_cols[2].button('🎁 Open Shop', key='buddy_shop_btn', use_container_width=True):
        st.info('🛍️ Shop coming up below!')
    status_html = f"""
      <div class='glass-panel-alt' style='margin-top:18px; animation: slideInLeft 0.6s ease 0.2s both;'>
        <div style='font-weight:700; margin-bottom:12px;'>📊 Buddy Status</div>
        <div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;'>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.1s both;'>🧬 {theme.get('mascot_name', buddy['species'].title())}</div>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.2s both;'>⚡ Energy: {get_today_progress_percent()}%</div>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.3s both;'>⭐ XP: {st.session_state.data['stats'].get('points', 0)}</div>
          <div class='status-pill' style='animation: popIn 0.6s ease 0.4s both;'>😊 {buddy['expression']}</div>
        </div>
      </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='glass-panel-alt' style='animation: slideInLeft 0.6s ease 0.3s both;'><div style='font-weight:700; margin-bottom:12px;'>🎨 Customize Buddy</div>", unsafe_allow_html=True)
    with st.form("buddy_customization"):
        name = st.text_input("Buddy name", value=buddy['name'], placeholder="Give your buddy a name!")
        custom_emoji = st.text_input("Custom emoji", value=buddy.get('custom_emoji', ''), max_chars=2, placeholder="😊")
        cols = st.columns(3)
        species_options = ["duckling", "hatchling", "swan", "hero", "phoenix", "robot", "alien"]
        eyes_options = ["sparkle", "sharp", "dreamy", "laser", "cyber"]
        mouth_options = ["smile", "grin", "wink", "glow", "nyan"]
        env_options = ["ocean", "space", "forest", "cyber", "desert", "volcano"]
        accessory_options = ["none", "crown", "glasses", "cape", "wings", "halo"]
        species = cols[0].selectbox("Species", species_options, index=species_options.index(buddy['species']) if buddy['species'] in species_options else 0)
        eyes = cols[1].selectbox("Eyes", eyes_options, index=eyes_options.index(buddy['eyes']) if buddy['eyes'] in eyes_options else 0)
        mouth = cols[2].selectbox("Mouth", mouth_options, index=mouth_options.index(buddy['mouth']) if buddy['mouth'] in mouth_options else 0)
        env = st.selectbox("Environment", env_options, index=env_options.index(buddy['environment']) if buddy['environment'] in env_options else 0)
        accessory = st.selectbox("Accessory", accessory_options, index=accessory_options.index(buddy.get('accessories', ['none'])[0]) if buddy.get('accessories') else 0)
        if st.form_submit_button("✓ Save Buddy Style", use_container_width=True):
            st.session_state.data["buddy"]["species"] = species
            st.session_state.data["buddy"]["eyes"] = eyes
            st.session_state.data["buddy"]["mouth"] = mouth
            st.session_state.data["buddy"]["environment"] = env
            st.session_state.data["buddy"]["name"] = name or buddy['name']
            st.session_state.data["buddy"]["custom_emoji"] = custom_emoji.strip()
            st.session_state.data["buddy"]["accessories"] = [] if accessory == "none" else [accessory]
            save_data_state("✅ Buddy appearance updated!")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
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
            if st.button("🔄 Reset Data", key="reset_settings", use_container_width=True):
                reset_all_data("✅ All data reset!")
                st.rerun()
        
        notifications = st.checkbox("Enable notifications", value=st.session_state.data["settings"].get("notifications", True))
        auto_save = st.checkbox("Auto save changes", value=st.session_state.data["settings"].get("auto_save", True))
        if st.button("Save settings", key="save_settings"):
            profile["name"] = name.strip()
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
            save_data_state("Settings updated.")
            query_page("Settings")
    reset_cols = st.columns(2)
    with reset_cols[0]:
        if st.button("Reset hydration logs only", key="reset_hydration"):
            reset_hydration_logs()
            st.rerun()
    with reset_cols[1]:
        if st.button("Reset everything", key="reset_everything"):
            reset_all_data()
            st.rerun()
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
            reset_all_data("Reset complete.")
            query_page("Settings")
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
    elif page == "Settings":
        render_settings(theme)
    else:
        render_home(theme)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="💧", layout="wide", initial_sidebar_state="expanded")
    init_state()
    theme_name = st.session_state.data["settings"].get("theme", "ocean")
    theme = style_page(theme_name)
    if not st.session_state.data["profile"].get("onboarding_complete", False):
        render_onboarding(theme)
        return
    page = get_current_page()

    render_left_settings_panel(page, theme)
    render_toast()
    render_welcome_header(theme)
    render_page(page, theme)

    if st.session_state.data.get("settings", {}).get("auto_save", True):
        save_data(st.session_state.data)

if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        print("Start Water Buddy with: streamlit run waterbuddy.py")
