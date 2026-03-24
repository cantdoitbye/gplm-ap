from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
import shapely.geometry

from app.database.models import GISRecord, VersionHistory, GUAAuditLog


def compute_hash(
    previous_hash: Optional[str],
    action: str,
    entity_id: str,
    old_values: Optional[Dict[str, Any]],
    new_values: Optional[Dict[str, Any]],
    timestamp: datetime
) -> str:
    data = f"{previous_hash}|{action}|{entity_id}|{json.dumps(old_values, sort_keys=True)}|{json.dumps(new_values, sort_keys=True)}|{timestamp.isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()


class GISRecordService:

    @staticmethod
    async def create_record(
        db: AsyncSession,
        record_type: str,
        geometry: Optional[Dict[str, Any]],
        properties: Optional[Dict[str, Any]],
        source: str,
        created_by: UUID
    ) -> GISRecord:
        record = GISRecord(
            id=uuid4(),
            record_type=record_type,
            properties=properties or {},
            status="active",
            source=source,
            created_by=created_by,
            is_deleted=False
        )
        
        if geometry:
            shape = shapely.geometry.shape(geometry)
            record.geometry = from_shape(shape, srid=4326)
        
        db.add(record)
        await db.flush()
        
        version = VersionHistory(
            id=uuid4(),
            record_id=record.id,
            version_number=1,
            snapshot={
                "record_type": record_type,
                "geometry": geometry,
                "properties": properties,
                "source": source
            },
            change_description="Initial record creation",
            created_by=created_by
        )
        db.add(version)
        
        last_audit = await db.execute(
            select(GUAAuditLog)
            .where(GUAAuditLog.record_id == record.id)
            .order_by(GUAAuditLog.created_at.desc())
            .limit(1)
        )
        last_audit_log = last_audit.scalar_one_or_none()
        previous_hash = last_audit_log.current_hash if last_audit_log else "0" * 64
        
        timestamp = datetime.utcnow()
        current_hash = compute_hash(
            previous_hash=previous_hash,
            action="create",
            entity_id=str(record.id),
            old_values=None,
            new_values={
                "record_type": record_type,
                "geometry": geometry,
                "properties": properties,
                "source": source
            },
            timestamp=timestamp
        )
        
        audit_log = GUAAuditLog(
            id=uuid4(),
            record_id=record.id,
            action="create",
            entity_type="gis_record",
            entity_id=record.id,
            old_values=None,
            new_values={
                "record_type": record_type,
                "geometry": geometry,
                "properties": properties,
                "source": source
            },
            previous_hash=previous_hash,
            current_hash=current_hash,
            created_at=timestamp,
            created_by=created_by
        )
        db.add(audit_log)
        
        await db.commit()
        await db.refresh(record)
        
        return record

    @staticmethod
    async def get_record(db: AsyncSession, record_id: UUID) -> Optional[GISRecord]:
        result = await db.execute(
            select(GISRecord).where(
                and_(
                    GISRecord.id == record_id,
                    GISRecord.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_records(
        db: AsyncSession,
        record_type: Optional[str] = None,
        status: Optional[str] = None,
        bbox: Optional[List[float]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[GISRecord]:
        query = select(GISRecord).where(GISRecord.is_deleted == False)
        
        if record_type:
            query = query.where(GISRecord.record_type == record_type)
        
        if status:
            query = query.where(GISRecord.status == status)
        
        if bbox and len(bbox) == 4:
            min_lon, min_lat, max_lon, max_lat = bbox
            envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            query = query.where(func.ST_Intersects(GISRecord.geometry, envelope))
        
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_record(
        db: AsyncSession,
        record_id: UUID,
        properties: Optional[Dict[str, Any]] = None,
        geometry: Optional[Dict[str, Any]] = None,
        change_description: Optional[str] = None,
        updated_by: UUID = None
    ) -> Optional[GISRecord]:
        record = await GISRecordService.get_record(db, record_id)
        if not record:
            return None
        
        old_values = {
            "properties": record.properties,
            "geometry": str(record.geometry) if record.geometry else None
        }
        
        if properties is not None:
            record.properties = properties
        if geometry is not None:
            shape = shapely.geometry.shape(geometry)
            record.geometry = from_shape(shape, srid=4326)
        
        new_values = {
            "properties": record.properties,
            "geometry": geometry
        }
        
        last_version = await db.execute(
            select(VersionHistory)
            .where(VersionHistory.record_id == record_id)
            .order_by(VersionHistory.version_number.desc())
            .limit(1)
        )
        last_version_obj = last_version.scalar_one_or_none()
        next_version = (last_version_obj.version_number + 1) if last_version_obj else 1
        
        version = VersionHistory(
            id=uuid4(),
            record_id=record_id,
            version_number=next_version,
            snapshot=new_values,
            change_description=change_description,
            created_by=updated_by
        )
        db.add(version)
        
        last_audit = await db.execute(
            select(GUAAuditLog)
            .where(GUAAuditLog.record_id == record_id)
            .order_by(GUAAuditLog.created_at.desc())
            .limit(1)
        )
        last_audit_log = last_audit.scalar_one_or_none()
        previous_hash = last_audit_log.current_hash if last_audit_log else "0" * 64
        
        timestamp = datetime.utcnow()
        current_hash = compute_hash(
            previous_hash=previous_hash,
            action="update",
            entity_id=str(record_id),
            old_values=old_values,
            new_values=new_values,
            timestamp=timestamp
        )
        
        audit_log = GUAAuditLog(
            id=uuid4(),
            record_id=record_id,
            action="update",
            entity_type="gis_record",
            entity_id=record_id,
            old_values=old_values,
            new_values=new_values,
            previous_hash=previous_hash,
            current_hash=current_hash,
            created_at=timestamp,
            created_by=updated_by
        )
        db.add(audit_log)
        
        record.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(record)
        
        return record

    @staticmethod
    async def delete_record(
        db: AsyncSession,
        record_id: UUID,
        deleted_by: UUID
    ) -> bool:
        record = await GISRecordService.get_record(db, record_id)
        if not record:
            return False
        
        old_values = {
            "is_deleted": False
        }
        new_values = {
            "is_deleted": True
        }
        
        record.is_deleted = True
        
        last_audit = await db.execute(
            select(GUAAuditLog)
            .where(GUAAuditLog.record_id == record_id)
            .order_by(GUAAuditLog.created_at.desc())
            .limit(1)
        )
        last_audit_log = last_audit.scalar_one_or_none()
        previous_hash = last_audit_log.current_hash if last_audit_log else "0" * 64
        
        timestamp = datetime.utcnow()
        current_hash = compute_hash(
            previous_hash=previous_hash,
            action="delete",
            entity_id=str(record_id),
            old_values=old_values,
            new_values=new_values,
            timestamp=timestamp
        )
        
        audit_log = GUAAuditLog(
            id=uuid4(),
            record_id=record_id,
            action="delete",
            entity_type="gis_record",
            entity_id=record_id,
            old_values=old_values,
            new_values=new_values,
            previous_hash=previous_hash,
            current_hash=current_hash,
            created_at=timestamp,
            created_by=deleted_by
        )
        db.add(audit_log)
        
        await db.commit()
        
        return True

    @staticmethod
    async def get_record_history(db: AsyncSession, record_id: UUID) -> List[VersionHistory]:
        result = await db.execute(
            select(VersionHistory)
            .where(VersionHistory.record_id == record_id)
            .order_by(VersionHistory.version_number.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_audit_trail(
        db: AsyncSession,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[GUAAuditLog]:
        query = select(GUAAuditLog)
        
        if entity_type:
            query = query.where(GUAAuditLog.entity_type == entity_type)
        
        if entity_id:
            query = query.where(GUAAuditLog.entity_id == entity_id)
        
        query = query.order_by(GUAAuditLog.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def verify_audit_chain(db: AsyncSession, record_id: UUID) -> Tuple[bool, Optional[int]]:
        result = await db.execute(
            select(GUAAuditLog)
            .where(GUAAuditLog.record_id == record_id)
            .order_by(GUAAuditLog.created_at.asc())
        )
        audit_logs = list(result.scalars().all())
        
        if not audit_logs:
            return (True, None)
        
        for i in range(1, len(audit_logs)):
            if audit_logs[i].previous_hash != audit_logs[i - 1].current_hash:
                return (False, i)
        
        return (True, None)
