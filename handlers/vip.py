import asyncio

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, VipCode
from database.github_sync import save_database
from locales import get_text

router = Router()

VIP_CODE_PATTERN = r"^VIP-[A-Z0-9]{6}$"


@router.message(F.text.regexp(VIP_CODE_PATTERN))
async def handle_vip_code(message: Message, db_user: User, db_session: AsyncSession):
    code_text = message.text.strip().upper()

    # Already VIP
    if db_user.is_vip:
        await message.answer(get_text(db_user.language, "vip_already"))
        return

    # Look up code
    vip_code = await db_session.scalar(
        select(VipCode).where(VipCode.code == code_text)
    )

    if not vip_code or vip_code.is_used:
        await message.answer(get_text(db_user.language, "vip_invalid"))
        return

    # Activate VIP
    vip_code.is_used = True
    vip_code.used_by = db_user.tg_id
    db_user.is_vip = True
    await db_session.commit()

    # Persist to GitHub (fire-and-forget)
    asyncio.create_task(save_database())

    await message.answer(
        get_text(db_user.language, "vip_activated"),
        parse_mode="HTML"
    )
