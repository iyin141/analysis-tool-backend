from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Any, Dict, Optional


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class DateRange(CamelModel):
    from_date: str  # maps to from in json
    to_date: str    # maps to to in json

    model_config = ConfigDict(
        alias_generator=lambda s: "from" if s == "from_date" else ("to" if s == "to_date" else to_camel(s)),
        populate_by_name=True,
    )


class HealthResponse(CamelModel):
    status: str
    version: str
    data_last_updated: Optional[str] = None
