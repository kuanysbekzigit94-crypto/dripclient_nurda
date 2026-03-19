import asyncio
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 1):
        self.limit = limit
        self.records = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
            
        user_id = event.from_user.id
        current_time = asyncio.get_event_loop().time()
        
        last_time = self.records.get(user_id, 0)
        
        if current_time - last_time < self.limit:
            # Drop the event if user is sending too fast
            return None
            
        self.records[user_id] = current_time
        return await handler(event, data)
