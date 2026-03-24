import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

import redis.asyncio as redis

from app.config import settings


@dataclass
class AgentMessage:
    id: uuid.UUID
    source_agent: str
    target_agent: str
    message_type: str
    payload: Dict[str, Any]
    created_at: datetime
    processed: bool = field(default=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "message_type": self.message_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "processed": self.processed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            id=uuid.UUID(data["id"]),
            source_agent=data["source_agent"],
            target_agent=data["target_agent"],
            message_type=data["message_type"],
            payload=data["payload"],
            created_at=datetime.fromisoformat(data["created_at"]),
            processed=data.get("processed", False),
        )


class MessageQueue:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self._subscribers: Dict[str, List[Callable]] = {}

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def publish(self, message: AgentMessage) -> uuid.UUID:
        r = await self._get_redis()
        await r.lpush(f"queue:{message.target_agent}", json.dumps(message.to_dict()))
        
        if message.target_agent in self._subscribers:
            for callback in self._subscribers[message.target_agent]:
                await callback(message)
        
        return message.id

    async def subscribe(self, agent_name: str, callback: Callable[[AgentMessage], None]) -> None:
        if agent_name not in self._subscribers:
            self._subscribers[agent_name] = []
        self._subscribers[agent_name].append(callback)

    async def get_messages(self, agent_name: str, limit: int = 100) -> List[AgentMessage]:
        r = await self._get_redis()
        messages_data = await r.lrange(f"queue:{agent_name}", 0, limit - 1)
        
        messages = []
        for msg_str in messages_data:
            try:
                msg_dict = json.loads(msg_str)
                messages.append(AgentMessage.from_dict(msg_dict))
            except (json.JSONDecodeError, KeyError):
                continue
        
        return messages

    async def mark_processed(self, message_id: uuid.UUID) -> None:
        r = await self._get_redis()
        
        keys = await r.keys("queue:*")
        for key in keys:
            messages = await r.lrange(key, 0, -1)
            for i, msg_str in enumerate(messages):
                try:
                    msg_dict = json.loads(msg_str)
                    if msg_dict.get("id") == str(message_id):
                        msg_dict["processed"] = True
                        await r.lset(key, i, json.dumps(msg_dict))
                        return
                except (json.JSONDecodeError, KeyError):
                    continue

    async def get_pending_count(self, agent_name: str) -> int:
        r = await self._get_redis()
        messages = await r.lrange(f"queue:{agent_name}", 0, -1)
        
        count = 0
        for msg_str in messages:
            try:
                msg_dict = json.loads(msg_str)
                if not msg_dict.get("processed", False):
                    count += 1
            except json.JSONDecodeError:
                count += 1
        
        return count

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None
