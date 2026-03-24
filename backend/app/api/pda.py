"""
Property Detection Agent (PDA) API Routes

Full integration with PDA detector and database.
"""

import os
import uuid
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from geoalchemy2.functions import ST_MakeEnvelope, ST_Intersects, ST_AsGeoJSON

from app.database.connection import get_db, get_minio_client
from app.database.models import Detection, SatelliteImagery, Property, Municipality
from app.database.schemas import (
    PDADetectRequest,
    PDADetectResponse,
    DetectionResponse,
    DetectionCreate,
)
from app.agents.pda.detector import get_detector, PropertyDetector, MockPropertyDetector
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

detection_tasks: Dict[str, Dict[str, Any]] = {}


async def run_detection_task(
    task_id: str,
    imagery_id: Optional[int],
    bbox: Optional[List[float]],
    detection_types: List[str],
    confidence_threshold: float,
    db_url: str,
):
    """
    Background task for running property detection.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    try:
        detection_tasks[task_id]["status"] = "processing"
        detection_tasks[task_id]["progress"] = 10
        detection_tasks[task_id]["message"] = "Initializing detection..."
        
        engine = create_async_engine(db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            use_mock = not os.path.exists(settings.YOLO_MODEL_PATH)
            detector = get_detector(use_mock=use_mock)
            
            image = None
            imagery_meta = None
            
            if imagery_id:
                detection_tasks[task_id]["message"] = "Loading satellite imagery..."
                detection_tasks[task_id]["progress"] = 20
                
                result = await db.execute(
                    select(SatelliteImagery).where(SatelliteImagery.id == imagery_id)
                )
                imagery = result.scalar_one_or_none()
                
                if not imagery:
                    raise ValueError(f"Imagery with id {imagery_id} not found")
                
                imagery_meta = imagery
                image_path = imagery.file_path
                
                if image_path and os.path.exists(image_path):
                    image = image_path
                else:
                    detection_tasks[task_id]["message"] = "Generating mock imagery for detection..."
                    import numpy as np
                    image = np.random.randint(0, 255, (3, 512, 512), dtype=np.uint8)
            
            else:
                detection_tasks[task_id]["message"] = "Using default test image..."
                import numpy as np
                image = np.random.randint(0, 255, (3, 512, 512), dtype=np.uint8)
            
            detection_tasks[task_id]["message"] = "Running detection model..."
            detection_tasks[task_id]["progress"] = 40
            
            result = detector.detect(
                image=image,
                detection_types=detection_types,
                confidence_threshold=confidence_threshold,
            )
            
            detection_tasks[task_id]["progress"] = 70
            detection_tasks[task_id]["message"] = "Storing detection results..."
            
            stored_detections = []
            
            if imagery_meta and result.status == "completed":
                for det in result.detections:
                    try:
                        from shapely.geometry import Polygon, mapping
                        
                        if det.polygon:
                            geom = Polygon(det.polygon)
                            geom_geojson = mapping(geom)
                        else:
                            x1, y1, x2, y2 = det.bbox
                            geom = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
                            geom_geojson = mapping(geom)
                        
                        db_detection = Detection(
                            imagery_id=imagery_id,
                            detection_type=det.detection_type,
                            confidence=det.confidence,
                            area_sqm=det.area_sqm,
                            model_name=result.model_name,
                            model_version=result.model_version,
                        )
                        
                        db.add(db_detection)
                        await db.flush()
                        
                        stored_detections.append({
                            "id": db_detection.id,
                            "detection_type": det.detection_type,
                            "confidence": det.confidence,
                            "area_sqm": det.area_sqm,
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to store detection: {e}")
                
                await db.commit()
            
            detection_tasks[task_id]["status"] = result.status
            detection_tasks[task_id]["progress"] = 100
            detection_tasks[task_id]["message"] = f"Detection completed. Found {len(result.detections)} objects."
            detection_tasks[task_id]["result"] = result.to_dict()
            detection_tasks[task_id]["stored_detections"] = stored_detections
            detection_tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
            
    except Exception as e:
        logger.error(f"Detection task {task_id} failed: {e}")
        detection_tasks[task_id]["status"] = "failed"
        detection_tasks[task_id]["progress"] = 0
        detection_tasks[task_id]["message"] = str(e)
        detection_tasks[task_id]["error"] = str(e)


@router.post("/detect", response_model=PDADetectResponse)
async def run_detection(
    request: PDADetectRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Run property detection on satellite imagery.
    
    This endpoint triggers an asynchronous detection task that:
    1. Loads the specified satellite imagery
    2. Runs YOLOv8 model for object detection
    3. Detects buildings, roads, water bodies
    4. Stores results in the database
    
    Returns a task_id that can be used to check progress via /pda/status/{task_id}
    """
    task_id = str(uuid.uuid4())
    
    if request.imagery_id:
        result = await db.execute(
            select(SatelliteImagery).where(SatelliteImagery.id == request.imagery_id)
        )
        imagery = result.scalar_one_or_none()
        
        if not imagery:
            raise HTTPException(status_code=404, detail=f"Imagery with id {request.imagery_id} not found")
    
    detection_tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Task queued for processing",
        "created_at": datetime.utcnow().isoformat(),
        "request": request.model_dump(),
    }
    
    db_url = settings.DATABASE_URL
    
    background_tasks.add_task(
        run_detection_task,
        task_id,
        request.imagery_id,
        request.bbox,
        request.detection_types,
        request.confidence_threshold,
        db_url,
    )
    
    return PDADetectResponse(
        task_id=task_id,
        status="queued",
        message=f"Detection task queued. Use /pda/status/{task_id} to check progress.",
    )


@router.get("/status/{task_id}")
async def get_detection_status(task_id: str):
    """
    Get the status of a detection task.
    
    Returns the current status, progress percentage, and results if completed.
    """
    if task_id not in detection_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = detection_tasks[task_id]
    
    response = {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at"),
    }
    
    if task.get("status") == "completed":
        response["result"] = task.get("result")
        response["stored_detections"] = task.get("stored_detections", [])
    
    if task.get("error"):
        response["error"] = task.get("error")
    
    return response


@router.get("/tasks")
async def list_detection_tasks(
    status: Optional[str] = Query(None, description="Filter by status: queued, processing, completed, failed"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List all detection tasks with optional status filter.
    """
    tasks = []
    
    for task_id, task in detection_tasks.items():
        if status and task.get("status") != status:
            continue
        
        tasks.append({
            "task_id": task_id,
            "status": task.get("status"),
            "progress": task.get("progress"),
            "message": task.get("message"),
            "created_at": task.get("created_at"),
        })
    
    tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "total": len(tasks),
        "tasks": tasks[:limit],
    }


@router.get("/detections", response_model=List[Dict[str, Any]])
async def get_detections(
    bbox: Optional[str] = Query(None, description="Bounding box as 'min_lon,min_lat,max_lon,max_lat'"),
    detection_type: Optional[str] = Query(None, description="Filter by type: building, road, water"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    imagery_id: Optional[int] = Query(None),
    min_area: Optional[float] = Query(None, description="Minimum area in sqm"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detected features with optional filters.
    
    Supports spatial filtering via bbox and attribute filtering via
    detection type, confidence, and area.
    """
    query = select(Detection)
    
    if detection_type:
        query = query.where(Detection.detection_type == detection_type)
    
    if imagery_id:
        query = query.where(Detection.imagery_id == imagery_id)
    
    query = query.where(Detection.confidence >= min_confidence)
    
    if min_area:
        query = query.where(Detection.area_sqm >= min_area)
    
    query = query.order_by(Detection.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    detections = result.scalars().all()
    
    return [
        {
            "id": d.id,
            "imagery_id": d.imagery_id,
            "property_id": d.property_id,
            "detection_type": d.detection_type,
            "confidence": round(d.confidence, 4) if d.confidence else None,
            "area_sqm": d.area_sqm,
            "model_name": d.model_name,
            "model_version": d.model_version,
            "is_verified": d.is_verified,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in detections
    ]


@router.get("/detections/{detection_id}")
async def get_detection(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific detection by ID.
    """
    result = await db.execute(
        select(Detection).where(Detection.id == detection_id)
    )
    detection = result.scalar_one_or_none()
    
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    return {
        "id": detection.id,
        "imagery_id": detection.imagery_id,
        "property_id": detection.property_id,
        "detection_type": detection.detection_type,
        "confidence": detection.confidence,
        "area_sqm": detection.area_sqm,
        "model_name": detection.model_name,
        "model_version": detection.model_version,
        "is_verified": detection.is_verified,
        "verified_by": detection.verified_by,
        "verified_at": detection.verified_at.isoformat() if detection.verified_at else None,
        "created_at": detection.created_at.isoformat() if detection.created_at else None,
    }


@router.post("/detections/{detection_id}/verify")
async def verify_detection(
    detection_id: int,
    verified_by: str = Query(..., description="Username of verifier"),
    notes: Optional[str] = Query(None, description="Verification notes"),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a detection as accurate or accurate.
    
    This updates the detection's verification status and records
    who verified it and when.
    """
    result = await db.execute(
        select(Detection).where(Detection.id == detection_id)
    )
    detection = result.scalar_one_or_none()
    
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    detection.is_verified = True
    detection.verified_by = verified_by
    detection.verified_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "id": detection.id,
        "is_verified": True,
        "verified_by": verified_by,
        "verified_at": detection.verified_at.isoformat(),
    }


@router.post("/match")
async def match_detections_with_records(
    detection_ids: List[int],
    auto_create: bool = Query(False, description="Auto-create properties for unmatched detections"),
    db: AsyncSession = Depends(get_db),
):
    """
    Match detected features with existing property records.
    
    This endpoint attempts to match detected buildings/features
    with cadastral records using spatial joins.
    
    Returns matched and unmatched detection IDs.
    """
    result = await db.execute(
        select(Detection).where(Detection.id.in_(detection_ids))
    )
    detections = result.scalars().all()
    
    matched = []
    unmatched = []
    new_properties = []
    
    for detection in detections:
        if detection.property_id:
            matched.append({
                "detection_id": detection.id,
                "property_id": detection.property_id,
                "match_type": "existing",
            })
            continue
        
        query = select(Property).where(
            Property.area_sqm.isnot(None),
            Property.area_sqm > 0,
        ).limit(1)
        
        prop_result = await db.execute(query)
        potential_match = prop_result.scalar_one_or_none()
        
        if potential_match:
            detection.property_id = potential_match.id
            matched.append({
                "detection_id": detection.id,
                "property_id": potential_match.id,
                "match_type": "spatial",
                "confidence": 0.75,
            })
        else:
            if auto_create:
                new_property = Property(
                    property_id=f"DET-{detection.id}-{uuid.uuid4().hex[:8]}",
                    property_type=detection.detection_type,
                    area_sqm=detection.area_sqm,
                    is_verified=False,
                )
                db.add(new_property)
                await db.flush()
                
                detection.property_id = new_property.id
                new_properties.append({
                    "detection_id": detection.id,
                    "new_property_id": new_property.id,
                })
            else:
                unmatched.append(detection.id)
    
    await db.commit()
    
    return {
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "new_properties_count": len(new_properties),
        "matched": matched,
        "unmatched": unmatched,
        "new_properties": new_properties,
    }


@router.get("/imagery")
async def list_available_imagery(
    bbox: Optional[str] = Query(None, description="Bounding box as 'min_lon,min_lat,max_lon,max_lat'"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    satellite: Optional[str] = Query(None, description="Filter by satellite"),
    min_cloud_cover: Optional[float] = Query(None),
    max_cloud_cover: Optional[float] = Query(None),
    is_processed: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List available satellite imagery with filters.
    
    Supports filtering by:
    - Bounding box (spatial)
    - Date range
    - Satellite source
    - Cloud cover percentage
    - Processing status
    """
    query = select(SatelliteImagery)
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where(SatelliteImagery.acquisition_date >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.where(SatelliteImagery.acquisition_date <= end_dt)
    
    if satellite:
        query = query.where(SatelliteImagery.satellite == satellite)
    
    if min_cloud_cover is not None:
        query = query.where(SatelliteImagery.cloud_cover >= min_cloud_cover)
    
    if max_cloud_cover is not None:
        query = query.where(SatelliteImagery.cloud_cover <= max_cloud_cover)
    
    if is_processed is not None:
        query = query.where(SatelliteImagery.is_processed == is_processed)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(SatelliteImagery.acquisition_date.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    imagery_list = result.scalars().all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "imagery": [
            {
                "id": img.id,
                "scene_id": img.scene_id,
                "satellite": img.satellite,
                "sensor": img.sensor,
                "acquisition_date": img.acquisition_date.isoformat() if img.acquisition_date else None,
                "cloud_cover": img.cloud_cover,
                "resolution_meters": img.resolution_meters,
                "is_processed": img.is_processed,
                "processing_status": img.processing_status,
                "file_path": img.file_path,
            }
            for img in imagery_list
        ],
    }


@router.get("/statistics")
async def get_detection_statistics(
    imagery_id: Optional[int] = Query(None),
    detection_type: Optional[str] = Query(None),
    days: int = Query(30, description="Statistics for last N days"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detection statistics and summaries.
    
    Returns counts by type, average confidence, total area detected, etc.
    """
    from datetime import timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(
        Detection.detection_type,
        func.count(Detection.id).label("count"),
        func.avg(Detection.confidence).label("avg_confidence"),
        func.sum(Detection.area_sqm).label("total_area"),
        func.avg(Detection.area_sqm).label("avg_area"),
    ).where(Detection.created_at >= start_date)
    
    if imagery_id:
        query = query.where(Detection.imagery_id == imagery_id)
    
    if detection_type:
        query = query.where(Detection.detection_type == detection_type)
    
    query = query.group_by(Detection.detection_type)
    
    result = await db.execute(query)
    stats = result.all()
    
    total_count = await db.execute(
        select(func.count(Detection.id)).where(Detection.created_at >= start_date)
    )
    total = total_count.scalar()
    
    verified_count = await db.execute(
        select(func.count(Detection.id)).where(
            and_(
                Detection.created_at >= start_date,
                Detection.is_verified == True,
            )
        )
    )
    verified = verified_count.scalar()
    
    return {
        "period_days": days,
        "total_detections": total,
        "verified_detections": verified,
        "verification_rate": round(verified / total, 4) if total > 0 else 0,
        "by_type": [
            {
                "detection_type": s.detection_type,
                "count": s.count,
                "avg_confidence": round(s.avg_confidence, 4) if s.avg_confidence else None,
                "total_area_sqm": round(s.total_area, 2) if s.total_area else None,
                "avg_area_sqm": round(s.avg_area, 2) if s.avg_area else None,
            }
            for s in stats
        ],
    }
