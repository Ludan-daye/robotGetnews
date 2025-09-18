from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None
    trace_id: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "message": "Success",
                "data": {},
                "trace_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class HealthResponse(BaseModel):
    status: str = "OK"
    version: str
    timestamp: str
    uptime: float


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict = {}
    trace_id: str

    class Config:
        schema_extra = {
            "example": {
                "error_code": "BAD_REQUEST",
                "message": "Invalid request parameters",
                "details": {"field": "validation error"},
                "trace_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


def success_response(data: Any = None, message: str = "Success", trace_id: Optional[str] = None) -> APIResponse:
    return APIResponse(code=200, message=message, data=data, trace_id=trace_id)


def error_response(
    code: int,
    error_code: str,
    message: str,
    details: dict = None,
    trace_id: Optional[str] = None
) -> dict:
    return {
        "error_code": error_code,
        "message": message,
        "details": details or {},
        "trace_id": trace_id
    }