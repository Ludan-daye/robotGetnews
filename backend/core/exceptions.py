from typing import Any, Dict, Optional
from fastapi import HTTPException
import uuid


class APIException(HTTPException):
    def __init__(
        self,
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        self.error_code = error_code or f"ERR_{status_code}"
        self.trace_id = str(uuid.uuid4())

        super().__init__(
            status_code=status_code,
            detail={
                "error_code": self.error_code,
                "message": self.message,
                "details": self.details,
                "trace_id": self.trace_id,
            }
        )


class BadRequestException(APIException):
    def __init__(self, message: str = "Bad Request", details: Optional[Dict[str, Any]] = None):
        super().__init__(400, message, details, "BAD_REQUEST")


class UnauthorizedException(APIException):
    def __init__(self, message: str = "Unauthorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(401, message, details, "UNAUTHORIZED")


class ForbiddenException(APIException):
    def __init__(self, message: str = "Forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(403, message, details, "FORBIDDEN")


class NotFoundException(APIException):
    def __init__(self, message: str = "Not Found", details: Optional[Dict[str, Any]] = None):
        super().__init__(404, message, details, "NOT_FOUND")


class ConflictException(APIException):
    def __init__(self, message: str = "Conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(409, message, details, "CONFLICT")


class InternalServerException(APIException):
    def __init__(self, message: str = "Internal Server Error", details: Optional[Dict[str, Any]] = None):
        super().__init__(500, message, details, "INTERNAL_SERVER_ERROR")


class ServiceUnavailableException(APIException):
    def __init__(self, message: str = "Service Unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(503, message, details, "SERVICE_UNAVAILABLE")