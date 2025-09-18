import time
from datetime import datetime
from fastapi import APIRouter
from core.config import settings
from core.response import HealthResponse

router = APIRouter()

# Store startup time
startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns system status, version, and uptime
    """
    current_time = time.time()
    uptime = current_time - startup_time

    return HealthResponse(
        status="OK",
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat() + "Z",
        uptime=round(uptime, 2)
    )