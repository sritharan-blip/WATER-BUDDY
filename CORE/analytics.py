import calendar
from datetime import date, timedelta


def get_weekly_totals(entries, goal):
    today = date.today()
    results = []
    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)
        day_key = day.strftime("%Y-%m-%d")
        total = sum(entry.get("amount", 0) for entry in entries if entry.get("date") == day_key)
        results.append((day.strftime("%a"), total))
    return results


def get_monthly_calendar(entries, year, month, goal):
    month_calendar = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
    result = []
    for week in month_calendar:
        row = []
        for day in week:
            day_key = day.strftime("%Y-%m-%d")
            total = sum(entry.get("amount", 0) for entry in entries if entry.get("date") == day_key)
            progress = int(min(100, (total / goal) * 100)) if goal else 0
            row.append({
                "date": day,
                "progress": progress,
                "is_current_month": day.month == month,
            })
        result.append(row)
    return result
