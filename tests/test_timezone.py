from app.utils.time import compute_d_minus_1_cutoff, get_delivery_day_slots, to_utc_iso


def test_d_minus_1_cutoff_computation():
    # For delivery date 2026-01-15, D-1 is 2026-01-14
    # In winter (January), Europe/London is UTC (GMT)
    cutoff = compute_d_minus_1_cutoff("2026-01-15", "09:00")
    iso_str = to_utc_iso(cutoff)
    assert iso_str == "2026-01-14T09:00:00Z"


def test_delivery_day_slots_generation():
    slots = get_delivery_day_slots("2026-01-01")
    assert len(slots) == 48
    assert slots[0].settlement_period == 1
    assert slots[0].start_time == "2026-01-01T00:00:00Z"
    assert slots[-1].settlement_period == 48
    assert slots[-1].start_time == "2026-01-01T23:30:00Z"
