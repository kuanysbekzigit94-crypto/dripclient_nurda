from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Product, Key, Purchase, Payment

async def get_user(session: AsyncSession, tg_id: int) -> User | None:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, tg_id: int, username: str) -> User:
    user = User(tg_id=tg_id, username=username)
    session.add(user)
    await session.commit()
    return user

async def get_or_create_user(session: AsyncSession, tg_id: int, username: str) -> User:
    user = await get_user(session, tg_id)
    if not user:
        user = await create_user(session, tg_id, username)
    return user
