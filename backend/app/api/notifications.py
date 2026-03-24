from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database.models import User
from app.api.auth import get_current_active_user
from app.services.notification_service import NotificationService


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    message: Optional[str]
    type: str
    is_read: bool
    created_at: datetime
    related_entity_type: Optional[str]
    related_entity_id: Optional[UUID]

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int


class UnreadCountResponse(BaseModel):
    unread_count: int


router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    notifications, total = await NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset
    )
    
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                title=n.title,
                message=n.message,
                type=n.type,
                is_read=n.is_read,
                created_at=n.created_at,
                related_entity_type=n.related_entity_type,
                related_entity_id=n.related_entity_id
            )
            for n in notifications
        ],
        total=total
    )


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return NotificationResponse(
        id=notification.id,
        title=notification.title,
        message=notification.message,
        type=notification.type,
        is_read=notification.is_read,
        created_at=notification.created_at,
        related_entity_type=notification.related_entity_type,
        related_entity_id=notification.related_entity_id
    )


@router.put("/read-all")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    count = await NotificationService.mark_all_as_read(
        db=db,
        user_id=current_user.id
    )
    
    return {"message": f"Marked {count} notifications as read", "count": count}


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_notification_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    count = await NotificationService.get_unread_count(
        db=db,
        user_id=current_user.id
    )
    
    return UnreadCountResponse(unread_count=count)
