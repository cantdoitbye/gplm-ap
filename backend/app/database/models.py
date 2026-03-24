"""
SQLAlchemy Database Models

All database models for the AIKOSH-5 application.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from geoalchemy2 import Geometry
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Municipality(Base):
    """Municipality/ULB model."""
    __tablename__ = "municipalities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    district = Column(String(100))
    state = Column(String(100), default="Andhra Pradesh")
    geometry = Column(Geometry("POLYGON", srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    properties = relationship("Property", back_populates="municipality")


class Property(Base):
    """Property/Land parcel model."""
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(String(100), unique=True, nullable=False, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"))
    
    survey_number = Column(String(100))
    subdivision = Column(String(50))
    owner_name = Column(String(255))
    property_type = Column(String(50))
    land_use = Column(String(50))
    
    area_sqm = Column(Float)
    built_area_sqm = Column(Float)
    
    geometry = Column(Geometry("POLYGON", srid=4326))
    centroid = Column(Geometry("POINT", srid=4326))
    
    is_verified = Column(Boolean, default=False)
    last_survey_date = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    municipality = relationship("Municipality", back_populates="properties")
    versions = relationship("PropertyVersion", back_populates="property")
    detections = relationship("Detection", back_populates="property")


class PropertyVersion(Base):
    """Property version history for audit trail."""
    __tablename__ = "property_versions"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    version = Column(Integer, nullable=False)
    
    previous_state = Column(JSON)
    current_state = Column(JSON)
    change_type = Column(String(50))
    change_description = Column(Text)
    
    changed_by = Column(String(100))
    change_reason = Column(Text)
    
    geometry = Column(Geometry("POLYGON", srid=4326))
    
    hash = Column(String(64))
    previous_hash = Column(String(64))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    property = relationship("Property", back_populates="versions")
    
    __table_args__ = (
        Index("ix_property_versions_property_version", "property_id", "version"),
    )


class SatelliteImagery(Base):
    """Satellite imagery metadata."""
    __tablename__ = "satellite_imagery"

    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(String(100), unique=True, nullable=False)
    satellite = Column(String(50))
    sensor = Column(String(50))
    
    acquisition_date = Column(DateTime, nullable=False)
    processing_date = Column(DateTime)
    
    cloud_cover = Column(Float)
    sun_elevation = Column(Float)
    sun_azimuth = Column(Float)
    
    geometry = Column(Geometry("POLYGON", srid=4326))
    
    resolution_meters = Column(Float)
    crs = Column(String(50))
    
    file_path = Column(String(500))
    file_size_mb = Column(Float)
    
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Detection(Base):
    """AI detection results."""
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"))
    imagery_id = Column(Integer, ForeignKey("satellite_imagery.id"))
    
    detection_type = Column(String(50), nullable=False)
    confidence = Column(Float)
    
    geometry = Column(Geometry("GEOMETRY", srid=4326))
    bbox = Column(Geometry("POLYGON", srid=4326))
    
    area_sqm = Column(Float)
    
    model_name = Column(String(100))
    model_version = Column(String(50))
    
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(100))
    verified_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    property = relationship("Property", back_populates="detections")


class ChangeDetection(Base):
    """Change detection results."""
    __tablename__ = "change_detections"

    id = Column(Integer, primary_key=True, index=True)
    imagery_before_id = Column(Integer, ForeignKey("satellite_imagery.id"))
    imagery_after_id = Column(Integer, ForeignKey("satellite_imagery.id"))
    
    change_type = Column(String(50), nullable=False)
    change_category = Column(String(50))
    
    confidence = Column(Float)
    severity = Column(String(20))
    
    geometry = Column(Geometry("GEOMETRY", srid=4326))
    area_sqm = Column(Float)
    
    is_verified = Column(Boolean, default=False)
    is_authorised = Column(Boolean)
    
    alert_generated = Column(Boolean, default=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """Alert model for detected changes."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    change_detection_id = Column(Integer, ForeignKey("change_detections.id"))
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(20))
    status = Column(String(20), default="new")
    
    municipality_id = Column(Integer, ForeignKey("municipalities.id"))
    assigned_to = Column(String(100))
    
    geometry = Column(Geometry("POINT", srid=4326))
    
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Blockchain-style audit log."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    
    previous_state = Column(JSON)
    current_state = Column(JSON)
    
    user_id = Column(String(100))
    ip_address = Column(String(50))
    user_agent = Column(String(255))
    
    block_hash = Column(String(64), unique=True, nullable=False)
    previous_hash = Column(String(64))
    nonce = Column(Integer)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )


class TrustScore(Base):
    """Trust score for entities."""
    __tablename__ = "trust_scores"

    id = Column(Integer, primary_key=True, index=True)
    
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    
    data_quality_score = Column(Float, default=0.0)
    compliance_score = Column(Float, default=0.0)
    coordination_score = Column(Float, default=0.0)
    verification_score = Column(Float, default=0.0)
    accuracy_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_trust_scores_entity", "entity_type", "entity_id"),
    )


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="viewer")
    department = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    notifications = relationship("Notification", back_populates="user")


class GISRecord(Base):
    """GIS Record model for GUA."""
    __tablename__ = "gis_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type = Column(String(50), nullable=False)
    geometry = Column(Geometry("GEOMETRY", srid=4326))
    properties = Column(JSON)
    status = Column(String(20), default="active")
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))
    is_deleted = Column(Boolean, default=False)
    
    versions = relationship("VersionHistory", back_populates="record")
    gua_audit_logs = relationship("GUAAuditLog", back_populates="record")


class VersionHistory(Base):
    """Version history model for GIS records."""
    __tablename__ = "version_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("gis_records.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON)
    change_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))
    
    record = relationship("GISRecord", back_populates="versions")
    
    __table_args__ = (
        Index("ix_version_history_record_version", "record_id", "version_number"),
    )


class GUAAuditLog(Base):
    """GUA Audit log model with hash-chaining."""
    __tablename__ = "gua_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("gis_records.id"))
    action = Column(String(20), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True))
    old_values = Column(JSON)
    new_values = Column(JSON)
    previous_hash = Column(String(64))
    current_hash = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))
    ip_address = Column(String(50))
    
    record = relationship("GISRecord", back_populates="gua_audit_logs")
    
    __table_args__ = (
        Index("ix_gua_audit_logs_record", "record_id"),
        Index("ix_gua_audit_logs_entity", "entity_type", "entity_id"),
    )


class Notification(Base):
    """Notification model for user alerts."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    type = Column(String(20), nullable=False)
    related_entity_type = Column(String(50))
    related_entity_id = Column(UUID(as_uuid=True))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")
    
    __table_args__ = (
        Index("ix_notifications_user", "user_id"),
    )
