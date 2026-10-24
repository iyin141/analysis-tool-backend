from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from typing import List, Tuple
from app.models.domain import HalfHourSlot

UK_TZ = ZoneInfo("Europe/London")
UTC_TZ = ZoneInfo("UTC")


def parse_iso(iso_str: str) -> datetime:
    """Parses ISO 8601 string ensuring UTC-aware datetime."""
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.astimezone(UTC_TZ)


def to_utc_iso(dt: datetime) -> str:
    """Formats datetime as ISO 8601 UTC with 'Z'."""
    utc_dt = dt.astimezone(UTC_TZ)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_d_minus_1_cutoff(delivery_date_str: str, cutoff_local_time_str: str = "09:00") -> datetime:
    """
    Given delivery date D (YYYY-MM-DD), computes cutoff time at D-1 in Europe/London,
    returned as a UTC-aware datetime.
    """
    d = date.fromisoformat(delivery_date_str)
    d_minus_1 = d - timedelta(days=1)
    
    parts = cutoff_local_time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    
    local_dt = datetime.combine(d_minus_1, time(hour, minute), tzinfo=UK_TZ)
    return local_dt.astimezone(UTC_TZ)


def get_delivery_day_slots(delivery_date_str: str) -> List[HalfHourSlot]:
    """
    Generates expected half-hour settlement periods for delivery day D in Europe/London.
    Typically 48 periods (00:00 to 23:30 local start times).
    """
    d = date.fromisoformat(delivery_date_str)
    # Start at 00:00 local time
    start_local = datetime.combine(d, time(0, 0), tzinfo=UK_TZ)
    next_day_local = datetime.combine(d + timedelta(days=1), time(0, 0), tzinfo=UK_TZ)
    
    slots: List[HalfHourSlot] = []
    curr = start_local
    period = 1
    
    while curr < next_day_local:
        curr_utc = curr.astimezone(UTC_TZ)
        slots.append(
            HalfHourSlot(
                start_time=to_utc_iso(curr_utc),
                settlement_date=delivery_date_str,
                settlement_period=period,
                hour_of_day=curr.hour,
            )
        )
        curr += timedelta(minutes=30)
        period += 1
        
    return slots
