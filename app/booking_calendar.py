"""Date boundaries shared by the booking API, seed data, and request workflow."""
import calendar
from datetime import date


def shift_years(day: date, years: int) -> date:
    year = day.year + years
    return date(year, day.month, min(day.day, calendar.monthrange(year, day.month)[1]))


def booking_window(today: date | None = None) -> tuple[date, date]:
    anchor = today or date.today()
    return shift_years(anchor, -2), shift_years(anchor, 2)
