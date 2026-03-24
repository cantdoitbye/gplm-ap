"""
Pydantic Schemas for API Request/Response Validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]


class MunicipalityBase(BaseModel):
    """Base municipality schema."""
    name: str
    code: str
    district: Optional[str] = None
    state: str = "Andhra Pradesh"


class MunicipalityCreate(MunicipalityBase):
    """Schema for creating a municipality."""
    geometry_geojson: Optional[Dict[str, Any]] = None


class MunicipalityResponse(MunicipalityBase):
    """Schema for municipality response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PropertyBase(BaseModel):
    """Base property schema."""
    property_id: str
    survey_number: Optional[str] = None
    subdivision: Optional[str] = None
    owner_name: Optional[str] = None
    property_type: Optional[str] = None
    land_use: Optional[str] = None
    area_sqm: Optional[float] = None
    built_area_sqm: Optional[float] = None


class PropertyCreate(PropertyBase):
    """Schema for creating a property."""
    municipality_id: int
    geometry_geojson: Optional[Dict[str, Any]] = None


class PropertyResponse(PropertyBase):
    """Schema for property response."""
    id: int
    municipality_id: int
    is_verified: bool
    last_survey_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DetectionBase(BaseModel):
    """Base detection schema."""
    detection_type: str
    confidence: float
    area_sqm: Optional[float] = None


class DetectionCreate(DetectionBase):
    """Schema for creating a detection."""
    property_id: Optional[int] = None
    imagery_id: int
    geometry_geojson: Dict[str, Any]
    bbox_geojson: Optional[Dict[str, Any]] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None


class DetectionResponse(DetectionBase):
    """Schema for detection response."""
    id: int
    property_id: Optional[int] = None
    imagery_id: int
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChangeDetectionBase(BaseModel):
    """Base change detection schema."""
    change_type: str
    change_category: Optional[str] = None
    confidence: float
    severity: Optional[str] = None
    area_sqm: Optional[float] = None


class ChangeDetectionCreate(ChangeDetectionBase):
    """Schema for creating a change detection."""
    imagery_before_id: int
    imagery_after_id: int
    geometry_geojson: Dict[str, Any]


class ChangeDetectionResponse(ChangeDetectionBase):
    """Schema for change detection response."""
    id: int
    imagery_before_id: int
    imagery_after_id: int
    is_verified: bool
    is_authorised: Optional[bool] = None
    alert_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    """Base alert schema."""
    title: str
    description: Optional[str] = None
    severity: str = "medium"


class AlertCreate(AlertBase):
    """Schema for creating an alert."""
    change_detection_id: int
    municipality_id: Optional[int] = None


class AlertResponse(AlertBase):
    """Schema for alert response."""
    id: int
    change_detection_id: int
    municipality_id: Optional[int] = None
    status: str
    assigned_to: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PDADetectRequest(BaseModel):
    """Request schema for PDA detection."""
    imagery_id: Optional[int] = None
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    detection_types: List[str] = Field(default=["building"], description="Types to detect: building, road, water")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class PDADetectResponse(BaseModel):
    """Response schema for PDA detection."""
    task_id: str
    status: str
    message: str


class CDACompareRequest(BaseModel):
    """Request schema for CDA comparison."""
    imagery_before_id: int
    imagery_after_id: int
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    change_types: List[str] = Field(
        default=["new_construction", "expansion", "demolition", "vegetation_change"],
        description="Types of changes to detect"
    )
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class CDACompareResponse(BaseModel):
    """Response schema for CDA comparison."""
    task_id: str
    status: str
    message: str


class GUARecordUpdate(BaseModel):
    """Schema for GUA record update."""
    property_id: int
    updates: Dict[str, Any]
    reason: str
    changed_by: str


class TrustScoreResponse(BaseModel):
    """Schema for trust score response."""
    entity_type: str
    entity_id: str
    data_quality_score: float
    compliance_score: float
    coordination_score: float
    verification_score: float
    accuracy_score: float
    overall_score: float
    last_updated: datetime


class Token(BaseModel):
    """JWT Token schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT Token payload schema."""
    sub: str
    exp: datetime
    iat: datetime
    role: Optional[str] = None


class TokenData(BaseModel):
    """Token data schema for current user extraction."""
    email: Optional[str] = None
    user_id: Optional[str] = None


class UserLogin(BaseModel):
    """User login schema."""
    email: str
    password: str


class UserCreate(BaseModel):
    """User creation schema."""
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"
    department: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    department: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
