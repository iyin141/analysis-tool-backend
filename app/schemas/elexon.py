from typing import Optional
from pydantic import BaseModel, ConfigDict


class FuelHHEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    dataset: str
    publishTime: str
    startTime: str
    settlementDate: str
    settlementPeriod: int
    fuelType: str
    generation: Optional[float] = 0.0


class WindforEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    dataset: str
    publishTime: str
    startTime: str
    generation: Optional[float] = 0.0
