"""
Database Connection Module

Handles PostgreSQL + PostGIS, Redis, and MinIO connections.
"""

from typing import Optional
import redis.asyncio as redis
from minio import Minio
from minio.error import S3Error
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


def get_async_database_url(url: str) -> str:
    """Convert database URL to async format."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    return url.replace("postgresql://", "postgresql+asyncpg://")


DATABASE_URL_ASYNC = get_async_database_url(settings.DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL_ASYNC,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_health() -> str:
    """Check database connectivity."""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            await session.execute(text("SELECT PostGIS_Version()"))
        return "healthy"
    except Exception as e:
        raise Exception(str(e))


redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def check_redis_health() -> str:
    """Check Redis connectivity."""
    try:
        client = await get_redis()
        await client.ping()
        return "healthy"
    except Exception as e:
        raise Exception(str(e))


minio_client: Optional[Minio] = None


def get_minio() -> Minio:
    """Get MinIO client instance."""
    global minio_client
    if minio_client is None:
        minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return minio_client


def get_minio_client() -> Minio:
    """Get MinIO client instance (alias for get_minio)."""
    return get_minio()


async def check_minio_health() -> str:
    """Check MinIO connectivity."""
    try:
        client = get_minio()
        client.list_buckets()
        return "healthy"
    except Exception as e:
        raise Exception(str(e))


async def init_minio_buckets():
    """Initialize MinIO buckets if they don't exist."""
    client = get_minio()
    
    buckets = [
        settings.MINIO_BUCKET_IMAGERY,
        settings.MINIO_BUCKET_GIS,
        settings.MINIO_BUCKET_MODELS,
    ]
    
    for bucket in buckets:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"Created MinIO bucket: {bucket}")
        except S3Error as e:
            print(f"Error creating bucket {bucket}: {e}")
