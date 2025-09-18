import time
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog

from core.config import settings
from core.exceptions import APIException
from core.response import HealthResponse, error_response
from api.health import router as health_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Application startup time
startup_time = time.time()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="GitHub project recommendation system with web-based configuration",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    # Generate trace ID for this request
    trace_id = request.headers.get("X-Trace-ID", f"req_{int(time.time() * 1000)}")

    # Log request
    logger.info(
        "Request received",
        method=request.method,
        url=str(request.url),
        trace_id=trace_id,
        user_agent=request.headers.get("user-agent"),
    )

    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log response
    logger.info(
        "Request processed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 3),
        trace_id=trace_id,
    )

    # Add trace ID to response headers
    response.headers["X-Trace-ID"] = trace_id

    return response


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            trace_id=exc.trace_id,
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            code=exc.status_code,
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            trace_id=request.headers.get("X-Trace-ID"),
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        trace_id=request.headers.get("X-Trace-ID"),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content=error_response(
            code=500,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            trace_id=request.headers.get("X-Trace-ID"),
        ),
    )


# Include routers
app.include_router(health_router, prefix="/api/v1", tags=["Health"])

# Import other routers
from api.auth import router as auth_router
from api.preferences import router as preferences_router
from api.projects import router as projects_router
from api.test_endpoints import router as test_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(preferences_router, prefix="/api/v1/preferences", tags=["Preferences"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(test_router, prefix="/api/v1/test", tags=["Testing"]) if settings.debug else None

# Mount static files for frontend
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    # Serve index.html at root path
    from fastapi.responses import FileResponse

    @app.get("/")
    async def serve_index():
        return FileResponse(frontend_path / "index.html")

    @app.get("/index.html")
    async def serve_index_explicit():
        return FileResponse(frontend_path / "index.html")

    @app.get("/app.js")
    async def serve_app_js():
        from fastapi.responses import FileResponse
        response = FileResponse(frontend_path / "app.js", media_type="application/javascript")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


@app.on_event("startup")
async def startup_event():
    logger.info(
        "Application starting",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Initialize database
    from core.init_db import init_database
    init_database()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )