from typing import List
from app.schemas.common import CamelModel


class HorizonBucket(CamelModel):
    horizon_min_hours: float
    horizon_max_hours: float
    n: int
    bias_mw: float
    mae_mw: float
    rmse_mw: float


class HorizonAnalysisResponse(CamelModel):
    horizon_bin_hours: float
    buckets: List[HorizonBucket]
