from typing import Any, Dict, Optional
from app.schemas.common import CamelModel


class ErrorDetail(CamelModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(CamelModel):
    error: ErrorDetail
