"""Business-hours rules for booking: opening hours, lunch, closed weekdays and national holidays.

Server-side config rather than DB tables (see README). Datetimes here are naive shop-local
wall-clock times, the same convention as `time_off` and `appointments.date`.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import holidays

SHOP_TIMEZONE = ZoneInfo("Asia/Tokyo")

# Slots start on the hour and fill the whole hour. 16:00 is the last slot (runs to 17:00).
FIRST_SLOT_HOUR = 10
LAST_SLOT_HOUR = 16
LUNCH_HOURS = {12}
SLOT_HOURS = tuple(
    hour for hour in range(FIRST_SLOT_HOUR, LAST_SLOT_HOUR + 1) if hour not in LUNCH_HOURS
)

# Python's weekday(): Monday=0 ... Sunday=6. (JavaScript's getDay() is Sunday=0, Thursday=4.)
THURSDAY = 3
SUNDAY = 6
CLOSED_WEEKDAYS = {THURSDAY, SUNDAY}

# Computes each year lazily on first lookup, including substitute and citizens' holidays.
JAPAN_HOLIDAYS = holidays.country_holidays("JP")


def shop_now() -> datetime:
    """Current time as a naive shop-local datetime, so it compares with stored DATETIMEs."""
    return datetime.now(SHOP_TIMEZONE).replace(tzinfo=None)


def is_closed_day(day: date) -> bool:
    """Weekly closed days and national holidays: the days the date picker fully disables."""
    return day.weekday() in CLOSED_WEEKDAYS or day in JAPAN_HOLIDAYS


def is_bookable_slot(slot: datetime) -> bool:
    """True if `slot` is an opening-hour start on an open day. Says nothing about the future,
    existing appointments or time off; those are checked by the booking service."""
    return (
        slot.minute == 0
        and slot.second == 0
        and slot.microsecond == 0
        and slot.hour in SLOT_HOURS
        and not is_closed_day(slot.date())
    )
