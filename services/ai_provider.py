import os


class AIHealthCoach:
    def get_tip(self, data):
        goal = data.get("profile", {}).get("goal", 2600)
        intake = sum(entry.get("amount", 0) for entry in data.get("entries", []) if entry.get("date") == __import__("datetime").date.today().strftime("%Y-%m-%d"))
        if intake >= goal:
            return "You’ve hit your hydration goal for today. Great job! Keep consistent with smaller refills."
        if intake >= goal * 0.75:
            return "You’re close to today’s goal — one or two more sips will get you there."
        if intake >= goal * 0.4:
            return "Good progress so far. Try topping up with a glass in the next hour."
        return "Aim for a steady sip schedule. Keep a water bottle nearby and take one sip every 30 minutes."


def get_coach():
    return AIHealthCoach()
