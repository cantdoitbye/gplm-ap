"""
AIKOSH-5 Geospatial AI Application

FastAPI application entry point with all routes and middleware.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Handles startup and shutdown events.
    """
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    try:
        from app.database.connection import engine, async_session_maker
        from app.database.models import Base
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"⚠️ Warning: Could not create database tables: {e}")
    
    yield
    
    print(f"👋 Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root() -> Dict:
    """Root endpoint returning API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict:
    """
    Health check endpoint.
    Returns the health status of all services.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "services": {
            "api": "healthy",
            "database": "unknown",
            "redis": "unknown",
            "minio": "unknown",
        },
    }
    
    try:
        from app.database.connection import check_database_health
        health_status["services"]["database"] = await check_database_health()
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    try:
        from app.database.connection import check_redis_health
        health_status["services"]["redis"] = await check_redis_health()
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    try:
        from app.database.connection import check_minio_health
        health_status["services"]["minio"] = await check_minio_health()
    except Exception as e:
        health_status["services"]["minio"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    if health_status["status"] == "degraded":
        return JSONResponse(
            status_code=503,
            content=health_status,
        )
    
    return health_status


@app.get("/ready", tags=["Health"])
async def readiness_check() -> Dict:
    """
    Readiness check endpoint.
    Returns whether the application is ready to receive traffic.
    """
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


from app.api import routes

app.include_router(routes.router, prefix="/api/v1")

from app.api.stubs import router as stubs_router
app.include_router(stubs_router, prefix="/api/v1")
