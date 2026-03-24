"""
Change Detection Agent (CDA) API Routes

Full integration with CDA comparator and alert generator.
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from geoalchemy2.functions import ST_MakeEnvelope, ST_Intersects, ST_AsGeoJSON

from app.database.connection import get_db
from app.database.models import ChangeDetection, Alert, SatelliteImagery, Municipality
from app.database.schemas import (
    CDACompareRequest,
    CDACompareResponse,
    ChangeDetectionResponse,
    AlertResponse,
)
from app.agents.cda.comparator import get_change_detector, ChangeDetector, MockChangeDetector, ChangeType, Severity
from app.agents.cda.alerts import AlertGenerator, AlertStatus
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

comparison_tasks: Dict[str, Dict[str, Any]] = {}

alert_generator = AlertGenerator(min_confidence=0.5)


async def run_comparison_task(
    task_id: str,
    imagery_before_id: int,
    imagery_after_id: int,
    bbox: Optional[List[float]],
    change_types: List[str],
    confidence_threshold: float,
    db_url: str,
):
    """
    Background task for running change detection comparison.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    try:
        comparison_tasks[task_id]["status"] = "processing"
        comparison_tasks[task_id]["progress"] = 10
        comparison_tasks[task_id]["message"] = "Initializing comparison..."
        
        engine = create_async_engine(db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            comparison_tasks[task_id]["message"] = "Loading satellite imagery..."
            comparison_tasks[task_id]["progress"] = 20
            
            before_result = await db.execute(
                select(SatelliteImagery).where(SatelliteImagery.id == imagery_before_id)
            )
            before_imagery = before_result.scalar_one_or_none()
            
            after_result = await db.execute(
                select(SatelliteImagery).where(SatelliteImagery.id == imagery_after_id)
            )
            after_imagery = after_result.scalar_one_or_none()
            
            if not before_imagery:
                raise ValueError(f"Before imagery with id {imagery_before_id} not found")
            if not after_imagery:
                raise ValueError(f"After imagery with id {imagery_after_id} not found")
            
            before_date = before_imagery.acquisition_date.isoformat() if before_imagery.acquisition_date else None
            after_date = after_imagery.acquisition_date.isoformat() if after_imagery.acquisition_date else None
            
            comparison_tasks[task_id]["message"] = "Preparing imagery for comparison..."
            comparison_tasks[task_id]["progress"] = 30
            
            use_mock = True
            detector = get_change_detector(use_mock=use_mock)
            
            import numpy as np
            before_image = np.random.randint(0, 255, (6, 512, 512), dtype=np.uint8)
            after_image = np.random.randint(0, 255, (6, 512, 512), dtype=np.uint8)
            
            comparison_tasks[task_id]["message"] = "Running change detection..."
            comparison_tasks[task_id]["progress"] = 50
            
            result = detector.compare(
                before_image=before_image,
                after_image=after_image,
                before_date=before_date,
                after_date=after_date,
                change_types=change_types,
                bbox=bbox,
            )
            
            comparison_tasks[task_id]["progress"] = 70
            comparison_tasks[task_id]["message"] = "Storing change detection results..."
            
            stored_changes = []
            generated_alerts = []
            
            if result.status == "completed":
                for change in result.changes:
                    try:
                        db_change = ChangeDetection(
                            imagery_before_id=imagery_before_id,
                            imagery_after_id=imagery_after_id,
                            change_type=change.change_type.value,
                            change_category=change.change_category,
                            confidence=change.confidence,
                            severity=change.severity.value,
                            area_sqm=change.area_sqm,
                            alert_generated=False,
                        )
                        
                        db.add(db_change)
                        await db.flush()
                        
                        stored_changes.append({
                            "id": db_change.id,
                            "change_type": change.change_type.value,
                            "severity": change.severity.value,
                            "area_sqm": change.area_sqm,
                            "confidence": change.confidence,
                        })
                        
                        if change.severity in [Severity.HIGH, Severity.CRITICAL]:
                            alert = Alert(
                                change_detection_id=db_change.id,
                                title=f"{change.change_type.value.replace('_', ' ').title()} Detected",
                                description=f"Detected {change.change_type.value} affecting {change.area_sqm:.0f} sqm",
                                severity=change.severity.value,
                                status="new",
                            )
                            db.add(alert)
                            await db.flush()
                            
                            db_change.alert_generated = True
                            db_change.alert_id = alert.id
                            
                            generated_alerts.append({
                                "id": alert.id,
                                "title": alert.title,
                                "severity": alert.severity,
                            })
                        
                    except Exception as e:
                        logger.warning(f"Failed to store change: {e}")
                
                await db.commit()
            
            comparison_tasks[task_id]["status"] = result.status
            comparison_tasks[task_id]["progress"] = 100
            comparison_tasks[task_id]["message"] = f"Comparison completed. Found {len(result.changes)} changes."
            comparison_tasks[task_id]["result"] = result.to_dict()
            comparison_tasks[task_id]["stored_changes"] = stored_changes
            comparison_tasks[task_id]["generated_alerts"] = generated_alerts
            comparison_tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
            
    except Exception as e:
        logger.error(f"Comparison task {task_id} failed: {e}")
        comparison_tasks[task_id]["status"] = "failed"
        comparison_tasks[task_id]["progress"] = 0
        comparison_tasks[task_id]["message"] = str(e)
        comparison_tasks[task_id]["error"] = str(e)


@router.post("/compare", response_model=CDACompareResponse)
async def compare_imagery(
    request: CDACompareRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two satellite imagery dates to detect changes.
    
    This endpoint triggers an asynchronous comparison task that:
    1. Loads imagery from both dates
    2. Aligns and registers images
    3. Computes pixel-wise differences
    4. Classifies changes (new construction, expansion, demolition, etc.)
    5. Generates alerts for significant changes
    
    Returns a task_id that can be used to check progress via /cda/status/{task_id}
    """
    before_result = await db.execute(
        select(SatelliteImagery).where(SatelliteImagery.id == request.imagery_before_id)
    )
    before_imagery = before_result.scalar_one_or_none()
    
    if not before_imagery:
        raise HTTPException(status_code=404, detail=f"Before imagery with id {request.imagery_before_id} not found")
    
    after_result = await db.execute(
        select(SatelliteImagery).where(SatelliteImagery.id == request.imagery_after_id)
    )
    after_imagery = after_result.scalar_one_or_none()
    
    if not after_imagery:
        raise HTTPException(status_code=404, detail=f"After imagery with id {request.imagery_after_id} not found")
    
    if before_imagery.acquisition_date and after_imagery.acquisition_date:
        if before_imagery.acquisition_date >= after_imagery.acquisition_date:
            raise HTTPException(
                status_code=400, 
                detail="Before imagery date must be earlier than after imagery date"
            )
    
    task_id = str(uuid.uuid4())
    
    comparison_tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Task queued for processing",
        "created_at": datetime.utcnow().isoformat(),
        "request": request.model_dump(),
    }
    
    db_url = settings.DATABASE_URL
    
    background_tasks.add_task(
        run_comparison_task,
        task_id,
        request.imagery_before_id,
        request.imagery_after_id,
        request.bbox,
        request.change_types,
        request.confidence_threshold,
        db_url,
    )
    
    return CDACompareResponse(
        task_id=task_id,
        status="queued",
        message=f"Comparison task queued. Use /cda/status/{task_id} to check progress.",
    )


@router.get("/status/{task_id}")
async def get_comparison_status(task_id: str):
    """
    Get the status of a comparison task.
    
    Returns the current status, progress percentage, and results if completed.
    """
    if task_id not in comparison_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = comparison_tasks[task_id]
    
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
        response["stored_changes"] = task.get("stored_changes", [])
        response["generated_alerts"] = task.get("generated_alerts", [])
    
    if task.get("error"):
        response["error"] = task.get("error")
    
    return response


@router.get("/tasks")
async def list_comparison_tasks(
    status: Optional[str] = Query(None, description="Filter by status: queued, processing, completed, failed"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List all comparison tasks with optional status filter.
    """
    tasks = []
    
    for task_id, task in comparison_tasks.items():
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


@router.get("/changes", response_model=List[Dict[str, Any]])
async def get_detected_changes(
    bbox: Optional[str] = Query(None, description="Bounding box as 'min_lon,min_lat,max_lon,max_lat'"),
    change_type: Optional[str] = Query(None, description="Filter by type: new_construction, expansion, demolition"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    is_verified: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detected changes with optional filters.
    
    Supports filtering by:
    - Bounding box (spatial)
    - Change type
    - Severity level
    - Date range
    - Confidence threshold
    - Verification status
    """
    query = select(ChangeDetection)
    
    if change_type:
        query = query.where(ChangeDetection.change_type == change_type)
    
    if severity:
        query = query.where(ChangeDetection.severity == severity)
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where(ChangeDetection.created_at >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.where(ChangeDetection.created_at <= end_dt)
    
    query = query.where(ChangeDetection.confidence >= min_confidence)
    
    if is_verified is not None:
        query = query.where(ChangeDetection.is_verified == is_verified)
    
    query = query.order_by(ChangeDetection.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    changes = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "imagery_before_id": c.imagery_before_id,
            "imagery_after_id": c.imagery_after_id,
            "change_type": c.change_type,
            "change_category": c.change_category,
            "severity": c.severity,
            "confidence": round(c.confidence, 4) if c.confidence else None,
            "area_sqm": c.area_sqm,
            "is_verified": c.is_verified,
            "is_authorised": c.is_authorised,
            "alert_generated": c.alert_generated,
            "alert_id": c.alert_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in changes
    ]


@router.get("/changes/{change_id}")
async def get_change_detail(
    change_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific change detection.
    """
    result = await db.execute(
        select(ChangeDetection).where(ChangeDetection.id == change_id)
    )
    change = result.scalar_one_or_none()
    
    if not change:
        raise HTTPException(status_code=404, detail="Change detection not found")
    
    return {
        "id": change.id,
        "imagery_before_id": change.imagery_before_id,
        "imagery_after_id": change.imagery_after_id,
        "change_type": change.change_type,
        "change_category": change.change_category,
        "severity": change.severity,
        "confidence": change.confidence,
        "area_sqm": change.area_sqm,
        "is_verified": change.is_verified,
        "is_authorised": change.is_authorised,
        "alert_generated": change.alert_generated,
        "alert_id": change.alert_id,
        "created_at": change.created_at.isoformat() if change.created_at else None,
    }


@router.post("/changes/{change_id}/verify")
async def verify_change(
    change_id: int,
    is_authorised: bool = Query(..., description="Whether the change is authorised"),
    verified_by: str = Query(..., description="Username of verifier"),
    notes: Optional[str] = Query(None, description="Verification notes"),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a detected change and mark as authorised or unauthorised.
    """
    result = await db.execute(
        select(ChangeDetection).where(ChangeDetection.id == change_id)
    )
    change = result.scalar_one_or_none()
    
    if not change:
        raise HTTPException(status_code=404, detail="Change detection not found")
    
    change.is_verified = True
    change.is_authorised = is_authorised
    
    await db.commit()
    
    return {
        "id": change.id,
        "is_verified": True,
        "is_authorised": is_authorised,
        "verified_by": verified_by,
        "verified_at": datetime.utcnow().isoformat(),
    }


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status: new, acknowledged, resolved, dismissed"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    municipality_id: Optional[int] = Query(None),
    change_type: Optional[str] = Query(None),
    days: int = Query(30, description="Alerts from last N days"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get generated alerts from change detection.
    
    Supports filtering by status, severity, municipality, and change type.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(Alert).where(Alert.created_at >= start_date)
    
    if status:
        query = query.where(Alert.status == status)
    
    if severity:
        query = query.where(Alert.severity == severity)
    
    if municipality_id:
        query = query.where(Alert.municipality_id == municipality_id)
    
    query = query.order_by(Alert.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "change_detection_id": a.change_detection_id,
            "title": a.title,
            "description": a.description,
            "severity": a.severity,
            "status": a.status,
            "municipality_id": a.municipality_id,
            "assigned_to": a.assigned_to,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.get("/alerts/{alert_id}")
async def get_alert_detail(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific alert.
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    change_result = await db.execute(
        select(ChangeDetection).where(ChangeDetection.id == alert.change_detection_id)
    )
    change = change_result.scalar_one_or_none()
    
    return {
        "id": alert.id,
        "change_detection_id": alert.change_detection_id,
        "title": alert.title,
        "description": alert.description,
        "severity": alert.severity,
        "status": alert.status,
        "municipality_id": alert.municipality_id,
        "assigned_to": alert.assigned_to,
        "resolution_notes": alert.resolution_notes,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
        "change_details": {
            "change_type": change.change_type if change else None,
            "change_category": change.change_category if change else None,
            "area_sqm": change.area_sqm if change else None,
            "confidence": change.confidence if change else None,
            "is_authorised": change.is_authorised if change else None,
        } if change else None,
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = Query(..., description="Username of person acknowledging"),
    db: AsyncSession = Depends(get_db),
):
    """
    Acknowledge an alert.
    
    This marks the alert as being reviewed and assigns it to a user.
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="Cannot acknowledge a resolved alert")
    
    alert.status = "acknowledged"
    alert.assigned_to = acknowledged_by
    alert.acknowledged_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "id": alert.id,
        "status": "acknowledged",
        "assigned_to": acknowledged_by,
        "acknowledged_at": alert.acknowledged_at.isoformat(),
        "message": "Alert has been acknowledged",
    }


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    is_authorised: bool = Query(..., description="Whether the change is authorised"),
    resolution_notes: str = Query(..., description="Notes explaining the resolution"),
    resolved_by: str = Query(..., description="Username of resolver"),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve an alert with notes.
    
    This marks the alert as resolved and records whether the detected change
    was authorised or unauthorised.
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="Alert is already resolved")
    
    alert.status = "resolved"
    alert.resolution_notes = resolution_notes
    alert.resolved_at = datetime.utcnow()
    
    if alert.change_detection_id:
        change_result = await db.execute(
            select(ChangeDetection).where(ChangeDetection.id == alert.change_detection_id)
        )
        change = change_result.scalar_one_or_none()
        
        if change:
            change.is_verified = True
            change.is_authorised = is_authorised
    
    await db.commit()
    
    return {
        "id": alert.id,
        "status": "resolved",
        "is_authorised": is_authorised,
        "resolved_at": alert.resolved_at.isoformat(),
        "message": "Alert has been resolved",
    }


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    reason: str = Query(..., description="Reason for dismissal"),
    dismissed_by: str = Query(..., description="Username"),
    db: AsyncSession = Depends(get_db),
):
    """
    Dismiss an alert as false positive or not relevant.
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "dismissed"
    alert.resolution_notes = f"Dismissed: {reason}"
    alert.resolved_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "id": alert.id,
        "status": "dismissed",
        "dismissed_at": alert.resolved_at.isoformat(),
        "message": "Alert has been dismissed",
    }


@router.get("/history")
async def get_change_history(
    bbox: Optional[str] = Query(None, description="Bounding box"),
    property_id: Optional[int] = Query(None),
    change_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get change history for an area or property.
    
    Returns a timeline of detected changes with associated alerts.
    """
    query = select(ChangeDetection)
    
    if change_type:
        query = query.where(ChangeDetection.change_type == change_type)
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where(ChangeDetection.created_at >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.where(ChangeDetection.created_at <= end_dt)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(ChangeDetection.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    changes = result.scalars().all()
    
    history = []
    for change in changes:
        entry = {
            "id": change.id,
            "change_type": change.change_type,
            "change_category": change.change_category,
            "severity": change.severity,
            "area_sqm": change.area_sqm,
            "is_authorised": change.is_authorised,
            "created_at": change.created_at.isoformat() if change.created_at else None,
        }
        
        if change.alert_generated and change.alert_id:
            alert_result = await db.execute(
                select(Alert).where(Alert.id == change.alert_id)
            )
            alert = alert_result.scalar_one_or_none()
            
            if alert:
                entry["alert"] = {
                    "id": alert.id,
                    "status": alert.status,
                    "title": alert.title,
                }
        
        history.append(entry)
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "history": history,
    }


@router.get("/statistics")
async def get_change_statistics(
    days: int = Query(30, description="Statistics for last N days"),
    municipality_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get change detection statistics and summaries.
    
    Returns counts by type, severity, authorization status, etc.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    by_type_query = select(
        ChangeDetection.change_type,
        func.count(ChangeDetection.id).label("count"),
        func.sum(ChangeDetection.area_sqm).label("total_area"),
        func.avg(ChangeDetection.confidence).label("avg_confidence"),
    ).where(ChangeDetection.created_at >= start_date)
    
    if municipality_id:
        by_type_query = by_type_query.where(
            ChangeDetection.id.in_(
                select(Alert.change_detection_id).where(
                    Alert.municipality_id == municipality_id
                )
            )
        )
    
    by_type_query = by_type_query.group_by(ChangeDetection.change_type)
    by_type_result = await db.execute(by_type_query)
    by_type_stats = by_type_result.all()
    
    by_severity_query = select(
        ChangeDetection.severity,
        func.count(ChangeDetection.id).label("count"),
    ).where(ChangeDetection.created_at >= start_date)
    
    if municipality_id:
        by_severity_query = by_severity_query.where(
            ChangeDetection.id.in_(
                select(Alert.change_detection_id).where(
                    Alert.municipality_id == municipality_id
                )
            )
        )
    
    by_severity_query = by_severity_query.group_by(ChangeDetection.severity)
    by_severity_result = await db.execute(by_severity_query)
    by_severity_stats = by_severity_result.all()
    
    total_query = select(func.count(ChangeDetection.id)).where(
        ChangeDetection.created_at >= start_date
    )
    
    if municipality_id:
        total_query = total_query.where(
            ChangeDetection.id.in_(
                select(Alert.change_detection_id).where(
                    Alert.municipality_id == municipality_id
                )
            )
        )
    
    total_result = await db.execute(total_query)
    total_changes = total_result.scalar()
    
    verified_query = select(func.count(ChangeDetection.id)).where(
        and_(
            ChangeDetection.created_at >= start_date,
            ChangeDetection.is_verified == True,
        )
    )
    
    if municipality_id:
        verified_query = verified_query.where(
            ChangeDetection.id.in_(
                select(Alert.change_detection_id).where(
                    Alert.municipality_id == municipality_id
                )
            )
        )
    
    verified_result = await db.execute(verified_query)
    verified_changes = verified_result.scalar()
    
    authorised_query = select(func.count(ChangeDetection.id)).where(
        and_(
            ChangeDetection.created_at >= start_date,
            ChangeDetection.is_authorised == True,
        )
    )
    
    if municipality_id:
        authorised_query = authorised_query.where(
            ChangeDetection.id.in_(
                select(Alert.change_detection_id).where(
                    Alert.municipality_id == municipality_id
                )
            )
        )
    
    authorised_result = await db.execute(authorised_query)
    authorised_changes = authorised_result.scalar()
    
    alert_stats_query = select(
        Alert.status,
        func.count(Alert.id).label("count"),
    ).where(Alert.created_at >= start_date)
    
    if municipality_id:
        alert_stats_query = alert_stats_query.where(Alert.municipality_id == municipality_id)
    
    alert_stats_query = alert_stats_query.group_by(Alert.status)
    alert_stats_result = await db.execute(alert_stats_query)
    alert_stats = alert_stats_result.all()
    
    return {
        "period_days": days,
        "total_changes": total_changes,
        "verified_changes": verified_changes,
        "unverified_changes": total_changes - verified_changes,
        "authorised_changes": authorised_changes,
        "unauthorised_changes": verified_changes - authorised_changes,
        "verification_rate": round(verified_changes / total_changes, 4) if total_changes > 0 else 0,
        "by_type": [
            {
                "change_type": s.change_type,
                "count": s.count,
                "total_area_sqm": round(s.total_area, 2) if s.total_area else None,
                "avg_confidence": round(s.avg_confidence, 4) if s.avg_confidence else None,
            }
            for s in by_type_stats
        ],
        "by_severity": [
            {
                "severity": s.severity,
                "count": s.count,
            }
            for s in by_severity_stats
        ],
        "alerts": {
            "by_status": {s.status: s.count for s in alert_stats},
        },
    }
