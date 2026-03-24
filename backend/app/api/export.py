from typing import Optional, List, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select
from geoalchemy2.shape import to_shape
import json
import csv
import io

from app.database.connection import get_db
from app.database.models import GISRecord, Property, Detection, ChangeDetection

router = APIRouter()


async def get_records_for_export(
    db: AsyncSession,
    record_type: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    bbox: Optional[List[float]]
) -> List[GISRecord]:
    query = select(GISRecord).where(GISRecord.is_deleted == False)
    
    if record_type:
        query = query.where(GISRecord.record_type == record_type)
    
    if start_date:
        query = query.where(GISRecord.created_at >= start_date)
    
    if end_date:
        query = query.where(GISRecord.created_at <= end_date)
    
    if bbox and len(bbox) == 4:
        min_lon, min_lat, max_lon, max_lat = bbox
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        query = query.where(func.ST_Intersects(GISRecord.geometry, envelope))
    
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/geojson")
async def export_geojson(
    record_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    db: AsyncSession = Depends(get_db),
):
    bbox_list = None
    if bbox:
        try:
            bbox_list = [float(x) for x in bbox.split(",")]
            if len(bbox_list) != 4:
                raise ValueError("bbox must have 4 values")
        except ValueError as e:
            return Response(
                content=json.dumps({"error": f"Invalid bbox format: {str(e)}"}),
                status_code=400,
                media_type="application/json"
            )
    
    records = await get_records_for_export(db, record_type, start_date, end_date, bbox_list)
    
    features = []
    for record in records:
        geometry_dict = None
        if record.geometry:
            try:
                shape = to_shape(record.geometry)
                geometry_dict = shape.__geo_interface__
            except Exception:
                pass
        
        feature = {
            "type": "Feature",
            "geometry": geometry_dict,
            "properties": {
                "id": str(record.id),
                "record_type": record.record_type,
                "status": record.status,
                "source": record.source,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                **(record.properties or {})
            }
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return Response(
        content=json.dumps(geojson, default=str),
        media_type="application/geo+json",
        headers={
            "Content-Disposition": "attachment; filename=export.geojson"
        }
    )


@router.get("/csv")
async def export_csv(
    record_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    records = await get_records_for_export(db, record_type, start_date, end_date, None)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ["id", "record_type", "status", "source", "created_at", "updated_at", "properties"]
    writer.writerow(headers)
    
    for record in records:
        row = [
            str(record.id),
            record.record_type,
            record.status,
            record.source,
            record.created_at.isoformat() if record.created_at else "",
            record.updated_at.isoformat() if record.updated_at else "",
            json.dumps(record.properties) if record.properties else ""
        ]
        writer.writerow(row)
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=export.csv"
        }
    )


@router.get("/detections")
async def export_detections(
    format: str = Query("json", regex="^(json|csv)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Detection)
    
    if start_date:
        query = query.where(Detection.created_at >= start_date)
    
    if end_date:
        query = query.where(Detection.created_at <= end_date)
    
    result = await db.execute(query)
    detections = list(result.scalars().all())
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [
            "id", "property_id", "imagery_id", "detection_type",
            "confidence", "area_sqm", "model_name", "model_version",
            "is_verified", "created_at"
        ]
        writer.writerow(headers)
        
        for detection in detections:
            row = [
                str(detection.id),
                str(detection.property_id) if detection.property_id else "",
                str(detection.imagery_id) if detection.imagery_id else "",
                detection.detection_type,
                detection.confidence or "",
                detection.area_sqm or "",
                detection.model_name or "",
                detection.model_version or "",
                detection.is_verified,
                detection.created_at.isoformat() if detection.created_at else ""
            ]
            writer.writerow(row)
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=detections.csv"
            }
        )
    else:
        detection_list = []
        for detection in detections:
            detection_data = {
                "id": str(detection.id),
                "property_id": str(detection.property_id) if detection.property_id else None,
                "imagery_id": str(detection.imagery_id) if detection.imagery_id else None,
                "detection_type": detection.detection_type,
                "confidence": detection.confidence,
                "area_sqm": detection.area_sqm,
                "model_name": detection.model_name,
                "model_version": detection.model_version,
                "is_verified": detection.is_verified,
                "created_at": detection.created_at.isoformat() if detection.created_at else None
            }
            detection_list.append(detection_data)
        
        return Response(
            content=json.dumps(detection_list, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=detections.json"
            }
        )
