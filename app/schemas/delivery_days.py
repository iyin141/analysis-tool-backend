from typing import List
from app.schemas.common import CamelModel


class DeliveryDayItem(CamelModel):
    delivery_date: str
    decision_cutoff: str
    has_forecast: bool
    has_actuals: bool


class DeliveryDaysResponse(CamelModel):
    timezone: str
    default_cutoff_local_time: str
    days: List[DeliveryDayItem]
