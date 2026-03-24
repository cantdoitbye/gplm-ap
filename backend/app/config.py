"""
AIKOSH-5 Configuration Module

Centralized configuration management using Pydantic Settings.
All environment variables are loaded and validated here.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AIKOSH-5 Geospatial AI"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "AI-Enabled Geospatial Property & Land-Use Monitoring"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://aikosh5:aikosh5_password@localhost:5432/aikosh5"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_IMAGERY: str = "satellite-imagery"
    MINIO_BUCKET_GIS: str = "gis-data"
    MINIO_BUCKET_MODELS: str = "ml-models"

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_STORAGE_BUCKET_NAME: str = "ooumph"
    AWS_S3_ENDPOINT_URL: Optional[str] = None
    AWS_S3_CUSTOM_DOMAIN: Optional[str] = None
    AWS_QUERYSTRING_AUTH: bool = False

    COPERNICUS_USERNAME: Optional[str] = None
    COPERNICUS_PASSWORD: Optional[str] = None
    COPERNICUS_API_URL: str = "https://catalogue.dataspace.copernicus.eu/odata/v1"

    GOOGLE_EARTH_ENGINE_KEY: Optional[str] = None

    MAPBOX_ACCESS_TOKEN: Optional[str] = None
    MAPBOX_STYLE_MAP: str = "mapbox://styles/mapbox/streets-v12"
    MAPBOX_STYLE_SATELLITE: str = "mapbox://styles/mapbox/satellite-streets-v12"

    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"

    GOOGLE_OPEN_BUILDINGS_URL: str = "https://sites.research.google/gr/open-buildings"

    MODEL_DEVICE: str = "cpu"
    MODEL_CONFIDENCE_THRESHOLD: float = 0.5
    YOLO_MODEL_PATH: str = "models/yolov8_building.pt"

    FL_SERVER_HOST: str = "localhost"
    FL_SERVER_PORT: int = 8080
    FL_MIN_CLIENTS: int = 3
    FL_ROUNDS: int = 10

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS_STR: str = "*"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        v = self.CORS_ORIGINS_STR.strip()
        if not v or v == "*":
            return ["*"]
        if v.startswith("["):
            import json
            return json.loads(v)
        return [origin.strip().strip('"').strip("'") for origin in v.split(",")]

    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    TRUST_SCORE_DECAY_DAYS: int = 30
    TRUST_SCORE_MIN_THRESHOLD: float = 0.3

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    OPENAI_API_KEY: Optional[str] = None

    SENTENCE_TRANSFORMERS_MODEL: Optional[str] = None
    SENTENCE_TRANSFORMERS_DEVICE: str = "cpu"

    MOCK_DATA_SEED: int = 42
    MOCK_PROPERTIES_COUNT: int = 1000
    MOCK_MUNICIPALITIES_COUNT: int = 3

    AOI_CENTER_LAT: float = 16.5062
    AOI_CENTER_LON: float = 80.6480

    USE_API_STUBS: bool = True

    BHUVAN_API_URL: str = "https://bhuvan.nrsc.gov.in"
    BHUVAN_API_KEY: Optional[str] = None
    NRSC_API_URL: str = "https://bhuvan.nrsc.gov.in/nrsc"
    NRSC_API_KEY: Optional[str] = None
    APSAC_API_URL: str = "https://apsac.ap.gov.in"
    APSAC_API_KEY: Optional[str] = None
    CDMA_API_URL: str = "https://cdma.ap.gov.in"
    CDMA_API_KEY: Optional[str] = None
    SSLR_API_URL: str = "https://sslr.ap.gov.in"
    SSLR_API_KEY: Optional[str] = None
    MEEBHOOMI_API_URL: str = "https://meebhoomi.ap.gov.in"
    MEEBHOOMI_API_KEY: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "env_parse_none_str": "",
    }


settings = Settings()
