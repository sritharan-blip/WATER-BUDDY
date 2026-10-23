# 💧 Water Buddy — Hydration Quest

A gamified hydration tracker built with [Streamlit](https://streamlit.io/). Log your drinks, hit your daily goal, grow your water-drop Buddy, earn Aqua Coins, and unlock cosmetics, all while building a healthy hydration habit.

Canva Story Board link: https://canva.link/ws7fkhxm3frq0ex
---

## Table of Contents

- [Features](#features)
- [Screens at a Glance](#screens-at-a-glance)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Data & Privacy](#data--privacy)
- [Themes](#themes)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)

---

## Features

### Hydration Tracking
- **Quick Add** buttons (100 / 250 / 330 / 500 / 750 ml) for one-tap logging
- **Hydration Lab** for custom amounts, drink types, and notes
- **Undo last log** and **reset logs** without losing settings
- Live progress bar with an animated liquid fill and daily timeline

### Personalized Goals
- Daily goal calculated from **age, weight, activity level, climate, and occupation**
- Age, occupation, and climate recommendation cards with tips
- Set a **custom goal** or apply any recommendation with one click

### Gamification
- **XP & Levels** earned from every drink you log
- **Aqua Coins** earned from logging and completing quests
- **Daily Quests** (reach your goal, keep a 7-day streak, verify containers) with claimable rewards
- **Achievement Hall** with Common, Rare, Epic, and Legendary badges
- **Streak tracking** to keep you consistent

### Your Buddy
- An animated water-drop companion whose expression changes with your hydration progress 
- **Buddy Shop** with wearables (glasses, beanie, scarf, katana, shirt), effects (sparkles), and legendary/mythic skins
- Equip, unequip, and manage items from **Your Vault**
- Rename your Buddy

### Insights & Analytics
- 7-day hydration trend, goal completion, and weekly summary charts (Altair)
- Monthly **Hydration Calendar** showing daily completion
- **Smart Insights** generated from your actual drinking habits

### Smart Tools
- **Container Verification**: upload a photo of your bottle and estimate capacity, fill level, and volume before logging
- **Rolling reminders**: configurable interval and amount, with in-app toasts
- Daily hydration tip

### Accounts & Data
- Local **username/password accounts** (PBKDF2-hashed passwords) with optional "remember me"
- **Backup / restore** your data as JSON
- Automatic refresh at local midnight

---

## Screens at a Glance

| Page | Purpose |
|------|---------|
| 🏠 Home | Progress hero, quick add, timeline, Buddy preview, daily tip |
| 💧 Hydrate | Detailed drink logging with type and notes |
| 📸 Verify | Image-based container analysis. Screenshot proof on how it works: https://drive.google.com/file/d/1bkn3AgWDeBdbkNZu5mr8ghy2hdHXZQ1E/view?usp=sharing. The estimated water intake can be logged from the verify page itself|
| 🐣 Buddy | Buddy lounge and customization shop |
| 🎯 Quests | Daily, weekly, and special missions |
| 🏆 Achievements | Badge collection and rarities |
| 📊 Analytics | Trend and completion charts |
| 🧠 Insights | Personalized hydration guidance |
| 📅 Calendar | Monthly goal-completion view |-Tap-to-view day details in the calendar
| ⏰ Reminders | Reminder plan and full tips list |
| ⚙️ Settings | Profile, goals, theme, backup, resets |

---

## Tech Stack

- **Python 3.10+**
- [Streamlit](https://streamlit.io/): UI framework
- [Altair](https://altair-viz.github.io/): charts
- [pandas](https://pandas.pydata.org/): data handling
---


---

## Project Structure

```
.
├── waterbuddy.py          # Main Streamlit app (UI, pages, state)
├── core/                  # Business logic
│   ├── analytics.py       #   Weekly totals and monthly calendar
│   ├── achievements.py    #   Achievement definitions and evaluation
│   ├── hydration.py       #   Goals, streaks, levels, recommendations
│   ├── insights.py        #   Smart insight generation
│   └── storage.py         #   Accounts and per-user data persistence
├── services/              # Pluggable providers
│   ├── ai_provider.py     #   HydroCoach tips
│   └── vision_provider.py #   Container image analysis
├── requirements.txt
├── run_waterbuddy.bat
├── run_waterbuddy.ps1
└── README.md
```

> The `core/` and `services/` folders are imported by `waterbuddy.py`. The app also supports upper-case folder names (`CORE`, `SERVICES`) for case-sensitive Linux deploys and can run from a nested `MAIN` folder.

---

## How It Works

- **State** lives in `st.session_state.data` and is saved per user through `core.storage`.
- **Navigation** uses a sidebar and the `?page=` URL query parameter.
- **Buddy avatar** is rendered as an inline SVG that reacts to your progress and equipped cosmetics.
- **Buddy expression** changes at each 25% milestone of your daily goal.
- **Rewards**: each log earns 1 Aqua Coin; XP is based on volume logged; quests grant bonus XP and coins.

---

## Data & Privacy

- All personal hydration data is stored **locally** in `~/.water_buddy`.
- Passwords are stored as salted PBKDF2-SHA256 hashes, never in plain text.
- No data is sent to external servers by the core app.
- Local data files and `.streamlit/secrets.toml` are excluded from Git via `.gitignore`.

Use **Settings → Data & Backup** to export or import your data as JSON.

---

## Themes

Six built-in themes: **Ocean** , **Midnight** , **Forest** , **Cyber** , **Sunset** , and **Day** . Switch anytime from Settings or with the Night/Day mode buttons on Home.

---

## Future Enhancements

The following features are planned for future updates and are **not available yet**:

- 🤖 **Gemini-powered HydroCoach chat** *(future enhancement)*: an AI chat coach for personalized hydration advice. For now, HydroCoach shows simple hydration tips.
- 🎤 **Voice input and voice-powered logging** *(future enhancement)*: expanded voice support for logging drinks hands-free. The current voice note button is only a prototype, so type in the Notes field for now.


---

## Testing 
The app is tested by various family members and Friends, the various inputs given by them have been changed accordingly in the app and saved.

## Credits 

- NAME: SRITHARAN N S 
- REGISTRATION NUMBER: 1000526
- SCHOOL NAME: JAIN VIDYALAYA 
- MENTOR NAME: SYED ALI BEEMA S

Stay hydrated! 💧
