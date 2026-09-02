from datetime import date


def generate_insights(data):
    entries = data.get("entries", [])
    today_key = date.today().strftime("%Y-%m-%d")
    today_total = sum(entry.get("amount", 0) for entry in entries if entry.get("date") == today_key)
    goal = data.get("profile", {}).get("goal", 2600)
    streak = data.get("stats", {}).get("streak", 0)
    unique_drinks = len({entry.get("drink", "water") for entry in entries if entry.get("date") == today_key})

    insights = []
    if today_total >= goal:
        insights.append({
            "title": "Goal reached!",
            "text": "You’ve hit today’s hydration target. Keep the momentum going with a light refill later.",
        })
    else:
        remaining = max(0, goal - today_total)
        insights.append({
            "title": "Goal status",
            "text": f"You need about {remaining} ml more to meet today’s goal. Small sips every 30 minutes will help.",
        })

    if streak >= 7:
        insights.append({
            "title": "Streak strength",
            "text": f"You’re on a {streak}-day streak. Consistency builds healthy hydration habits.",
        })
    else:
        insights.append({
            "title": "Build your streak",
            "text": "Stick to a steady drinking schedule and aim for a short afternoon refill to power your next streak day.",
        })

    if unique_drinks >= 3:
        insights.append({
            "title": "Hydration variety",
            "text": "Nice variety today — mixing water, tea, and other drinks helps you stay engaged with hydration.",
        })
    else:
        insights.append({
            "title": "Try a new drink",
            "text": "Add a different drink type to your next log to keep hydration interesting and balanced.",
        })

    return insights
