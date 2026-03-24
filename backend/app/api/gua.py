from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.agents.gua.records import GISRecordService


class GISRecordCreate(BaseModel):
    record_type: str
    geometry: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    source: str
    created_by: UUID


class GISRecordUpdate(BaseModel):
    properties: Optional[Dict[str, Any]] = None
    geometry: Optional[Dict[str, Any]] = None
    change_description: Optional[str] = None
    updated_by: UUID


class GISRecordResponse(BaseModel):
    id: UUID
    record_type: str
    geometry: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    status: str
    source: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    is_deleted: bool

    class Config:
        from_attributes = True


class VersionHistoryResponse(BaseModel):
    id: UUID
    record_id: UUID
    version_number: int
    snapshot: Optional[Dict[str, Any]] = None
    change_description: Optional[str] = None
    created_at: datetime
    created_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class GUAAuditLogResponse(BaseModel):
    id: UUID
    record_id: Optional[UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class AuditChainVerificationResponse(BaseModel):
    is_valid: bool
    broken_at_index: Optional[int] = None
    message: str


router = APIRouter(tags=["GUA"])


@router.get("/records", response_model=List[GISRecordResponse])
async def list_records(
    record_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    bbox_list = None
    if bbox:
        try:
            bbox_list = [float(x) for x in bbox.split(",")]
            if len(bbox_list) != 4:
                raise ValueError("bbox must have 4 values")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid bbox format: {str(e)}")
    
    records = await GISRecordService.list_records(
        db=db,
        record_type=record_type,
        status=status,
        bbox=bbox_list,
        limit=limit,
        offset=offset
    )
    
    response = []
    for record in records:
        geometry_dict = None
        if record.geometry:
            from geoalchemy2.shape import to_shape
            shape = to_shape(record.geometry)
            geometry_dict = shape.__geo_interface__
        
        response.append(GISRecordResponse(
            id=record.id,
            record_type=record.record_type,
            geometry=geometry_dict,
            properties=record.properties,
            status=record.status,
            source=record.source,
            created_at=record.created_at,
            updated_at=record.updated_at,
            created_by=record.created_by,
            is_deleted=record.is_deleted
        ))
    
    return response


@router.post("/records", response_model=GISRecordResponse, status_code=201)
async def create_record(
    record: GISRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    created_record = await GISRecordService.create_record(
        db=db,
        record_type=record.record_type,
        geometry=record.geometry,
        properties=record.properties,
        source=record.source,
        created_by=record.created_by
    )
    
    geometry_dict = None
    if created_record.geometry:
        from geoalchemy2.shape import to_shape
        shape = to_shape(created_record.geometry)
        geometry_dict = shape.__geo_interface__
    
    return GISRecordResponse(
        id=created_record.id,
        record_type=created_record.record_type,
        geometry=geometry_dict,
        properties=created_record.properties,
        status=created_record.status,
        source=created_record.source,
        created_at=created_record.created_at,
        updated_at=created_record.updated_at,
        created_by=created_record.created_by,
        is_deleted=created_record.is_deleted
    )


@router.get("/records/{record_id}", response_model=GISRecordResponse)
async def get_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    record = await GISRecordService.get_record(db=db, record_id=record_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    geometry_dict = None
    if record.geometry:
        from geoalchemy2.shape import to_shape
        shape = to_shape(record.geometry)
        geometry_dict = shape.__geo_interface__
    
    return GISRecordResponse(
        id=record.id,
        record_type=record.record_type,
        geometry=geometry_dict,
        properties=record.properties,
        status=record.status,
        source=record.source,
        created_at=record.created_at,
        updated_at=record.updated_at,
        created_by=record.created_by,
        is_deleted=record.is_deleted
    )


@router.put("/records/{record_id}", response_model=GISRecordResponse)
async def update_record(
    record_id: UUID,
    update: GISRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated_record = await GISRecordService.update_record(
        db=db,
        record_id=record_id,
        properties=update.properties,
        geometry=update.geometry,
        change_description=update.change_description,
        updated_by=update.updated_by
    )
    
    if not updated_record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    geometry_dict = None
    if updated_record.geometry:
        from geoalchemy2.shape import to_shape
        shape = to_shape(updated_record.geometry)
        geometry_dict = shape.__geo_interface__
    
    return GISRecordResponse(
        id=updated_record.id,
        record_type=updated_record.record_type,
        geometry=geometry_dict,
        properties=updated_record.properties,
        status=updated_record.status,
        source=updated_record.source,
        created_at=updated_record.created_at,
        updated_at=updated_record.updated_at,
        created_by=updated_record.created_by,
        is_deleted=updated_record.is_deleted
    )


@router.delete("/records/{record_id}")
async def delete_record(
    record_id: UUID,
    deleted_by: UUID,
    db: AsyncSession = Depends(get_db),
):
    success = await GISRecordService.delete_record(
        db=db,
        record_id=record_id,
        deleted_by=deleted_by
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return {"record_id": str(record_id), "status": "deleted", "message": "Record has been soft-deleted"}


@router.get("/records/{record_id}/history", response_model=List[VersionHistoryResponse])
async def get_record_history(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    history = await GISRecordService.get_record_history(db=db, record_id=record_id)
    
    return [
        VersionHistoryResponse(
            id=version.id,
            record_id=version.record_id,
            version_number=version.version_number,
            snapshot=version.snapshot,
            change_description=version.change_description,
            created_at=version.created_at,
            created_by=version.created_by
        )
        for version in history
    ]


@router.get("/audit", response_model=List[GUAAuditLogResponse])
async def get_audit_trail(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    audit_logs = await GISRecordService.get_audit_trail(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit
    )
    
    return [
        GUAAuditLogResponse(
            id=log.id,
            record_id=log.record_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_values=log.old_values,
            new_values=log.new_values,
            previous_hash=log.previous_hash,
            current_hash=log.current_hash,
            created_at=log.created_at,
            created_by=log.created_by,
            ip_address=log.ip_address
        )
        for log in audit_logs
    ]


@router.get("/audit/verify/{record_id}", response_model=AuditChainVerificationResponse)
async def verify_audit_chain(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    is_valid, broken_at_index = await GISRecordService.verify_audit_chain(
        db=db,
        record_id=record_id
    )
    
    if is_valid:
        message = "Audit chain integrity verified successfully"
    else:
        message = f"Audit chain integrity broken at index {broken_at_index}"
    
    return AuditChainVerificationResponse(
        is_valid=is_valid,
        broken_at_index=broken_at_index,
        message=message
    )
