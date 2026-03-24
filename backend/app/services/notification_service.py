from typing import Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select, update

from app.database.models import Notification


class NotificationService:

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: UUID,
        title: str,
        message: str,
        type: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[UUID] = None
    ) -> Notification:
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            is_read=False
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        return notification

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Notification], int]:
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        notifications = list(result.scalars().all())
        
        return notifications, total

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID
    ) -> Optional[Notification]:
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            return None
        
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        
        return notification

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            .values(is_read=True)
            .returning(Notification.id)
        )
        
        updated_ids = result.fetchall()
        await db.commit()
        
        return len(updated_ids)

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(
            select(func.count()).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
        )
        return result.scalar() or 0
