from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from database.models import User, Key, Payment
from config import config
from database.github_sync import save_database
import asyncio

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


class AdminUserState(StatesGroup):
    waiting_for_ban_id         = State()
    waiting_for_add_bal_id     = State()
    waiting_for_add_bal_amount = State()
    waiting_for_info_id        = State()


# ─── BAN / UNBAN ─────────────────────────────────────────────────

@router.message(F.text == "🚫 Ban User")
async def ban_user_start(message: Message, state: FSMContext, db_user: User):
    if not is_admin(db_user.tg_id):
        return
    await state.set_state(AdminUserState.waiting_for_ban_id)
    await message.answer(
        "🚫 <b>Пайдаланушыны блоктау / бұғатты алу</b>\n\n"
        "Telegram ID-ін жіберіңіз:",
        parse_mode="HTML"
    )


@router.message(AdminUserState.waiting_for_ban_id)
async def process_ban_user(message: Message, state: FSMContext, db_session: AsyncSession):
    query = message.text.strip() if message.text else ""
    if not query:
        await message.answer("⚠️ Жіберіңіз.")
        return

    user = None

    if query.isdigit() and len(query) < 10:
        pass # Handle below

    if query.startswith("+") or (query.isdigit() and len(query) >= 10):
        # Search by phone number
        normalized = query if query.startswith("+") else "+" + query
        user = await db_session.scalar(
            select(User).where(or_(User.phone_number == query, User.phone_number == normalized))
        )
    elif query.isdigit():
        # Search by Telegram ID
        user = await db_session.scalar(select(User).where(User.tg_id == int(query)))
    else:
        # Search by username (with or without @)
        uname = query.lstrip("@")
        user = await db_session.scalar(select(User).where(func.lower(User.username) == func.lower(uname)))

    if not user:
        await message.answer(
            f"❌ <b>Табылмады</b>\n\n"
            f"<code>{query}</code> бойынша пайдаланушы жоқ.\n"
            f"ID, @username немесе телефон нөмірін тексеріп қайта жіберіңіз.",
            parse_mode="HTML"
        )
    else:
        user.is_banned = not user.is_banned
        await db_session.commit()
        asyncio.create_task(save_database())
        status = "🔴 БЛОКТАЛДЫ" if user.is_banned else "🟢 БҰҒАТ АЛЫНДЫ"
        await message.answer(
            f"✅ Пайдаланушы <code>{user.tg_id} / @{user.username or 'no_username'}</code> — {status}",
            parse_mode="HTML"
        )

    await state.clear()



# ─── ADD BALANCE ─────────────────────────────────────────────────

@router.message(F.text == "💰 Add Balance")
async def add_bal_start(message: Message, state: FSMContext, db_user: User):
    if not is_admin(db_user.tg_id):
        return
    await state.set_state(AdminUserState.waiting_for_add_bal_id)
    await message.answer(
        "💰 <b>Баланс қосу</b>\n\n"
        "Пайдаланушының айдиын(Telegram ID) немесе @username жіберіңіз:",
        parse_mode="HTML"
    )


@router.message(AdminUserState.waiting_for_add_bal_id)
async def process_add_bal_id(message: Message, state: FSMContext, db_session: AsyncSession):
    query = message.text.strip() if message.text else ""
    if not query:
        await message.answer("⚠️ Жіберіңіз.")
        return

    user = None

    if query.isdigit() and len(query) < 10:
        pass # Handle below

    if query.startswith("+") or (query.isdigit() and len(query) >= 10):
        # Search by phone number
        normalized = query if query.startswith("+") else "+" + query
        user = await db_session.scalar(
            select(User).where(or_(User.phone_number == query, User.phone_number == normalized))
        )
    elif query.isdigit():
        # Search by Telegram ID
        user = await db_session.scalar(select(User).where(User.tg_id == int(query)))
    else:
        # Search by username (with or without @)
        uname = query.lstrip("@")
        user = await db_session.scalar(select(User).where(func.lower(User.username) == func.lower(uname)))

    if not user:
        await message.answer(
            f"❌ <b>Табылмады</b>\n\n"
            f"<code>{query}</code> бойынша пайдаланушы жоқ.\n"
            f"ID, @username немесе телефон нөмірін тексеріп қайта жіберіңіз.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    await state.update_data(target_user_id=user.tg_id)
    await state.set_state(AdminUserState.waiting_for_add_bal_amount)
    await message.answer(
        f"✅ Пайдаланушы табылды!\n\n"
        f"👤 @{user.username or 'no_username'}\n"
        f"💳 Ағымдағы баланс: <b>{user.balance:,.0f} ₸</b>\n\n"
        f"Қосу керек соманы жіберіңіз (теріс мән шегеру үшін, мысалы: -500):",
        parse_mode="HTML"
    )


@router.message(AdminUserState.waiting_for_add_bal_amount)
async def process_add_bal_amount(message: Message, state: FSMContext, db_session: AsyncSession):
    try:
        amount = float(message.text.strip().replace(",", "."))
    except (ValueError, AttributeError):
        await message.answer("⚠️ Жарамды сан жіберіңіз. Мысалы: 5000 немесе -500")
        return

    data = await state.get_data()
    user_id = data["target_user_id"]

    user = await db_session.scalar(select(User).where(User.tg_id == user_id))
    if user:
        user.balance += amount
        await db_session.commit()
        asyncio.create_task(save_database())
        action = "➕ Қосылды" if amount >= 0 else "➖ Шегерілді"
        await message.answer(
            f"✅ <b>Сәтті!</b>\n\n"
            f"👤 @{user.username or user_id}\n"
            f"{action}: <b>{abs(amount):,.0f} ₸</b>\n"
            f"💳 Жаңа баланс: <b>{user.balance:,.0f} ₸</b>",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Пайдаланушы табылмады.")

    await state.clear()


# ─── USER INFO ───────────────────────────────────────────────────

@router.message(F.text == "👁 User Info")
async def user_info_start(message: Message, state: FSMContext, db_user: User):
    if not is_admin(db_user.tg_id):
        return
    await state.set_state(AdminUserState.waiting_for_info_id)
    await message.answer(
        "👁 <b>ПАЙДАЛАНУШЫ АҚПАРАТЫ</b>\n\n"
        "Мыналардың бірін жіберіңіз:\n\n"
        "• Telegram ID → <code>123456789</code>\n"
        "• Username → <code>@username</code>\n"
        "• Телефон → <code>+77011234567</code>",
        parse_mode="HTML"
    )


@router.message(AdminUserState.waiting_for_info_id)
async def process_user_info(message: Message, state: FSMContext, db_session: AsyncSession):
    query = message.text.strip() if message.text else ""
    if not query:
        await message.answer("⚠️ Жіберіңіз.")
        return

    user = None

    if query.isdigit() and len(query) < 10:
        # Search by Telegram ID (typically < 10 digits unless it's a very long ID, but phones are usually longer)
        # Actually IDs can be up to 10-15 digits now, so checking if it starts with + or is just digits
        pass # Handle below

    if query.startswith("+") or (query.isdigit() and len(query) >= 10):
        # Search by phone number
        normalized = query if query.startswith("+") else "+" + query
        user = await db_session.scalar(
            select(User).where(or_(User.phone_number == query, User.phone_number == normalized))
        )
    elif query.isdigit():
        # Search by Telegram ID
        user = await db_session.scalar(select(User).where(User.tg_id == int(query)))
    else:
        # Search by username (with or without @)
        uname = query.lstrip("@")
        user = await db_session.scalar(select(User).where(func.lower(User.username) == func.lower(uname)))

    if not user:
        await message.answer(
            f"❌ <b>Табылмады</b>\n\n"
            f"<code>{query}</code> бойынша пайдаланушы жоқ.\n"
            f"ID, @username немесе телефон нөмірін тексеріп қайта жіберіңіз.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    keys_count = await db_session.scalar(
        select(func.count(Key.id)).where(Key.used_by == user.tg_id)
    ) or 0
    approved_payments = await db_session.scalar(
        select(func.sum(Payment.amount)).where(
            Payment.user_tg_id == user.tg_id, Payment.status == "approved"
        )
    ) or 0

    status_icon = "🔴 Блокталған" if user.is_banned else "🟢 Белсенді"
    phone_str = user.phone_number or "—"
    username_str = f"@{user.username}" if user.username else "—"

    text = (
        f"👁 <b>ПАЙДАЛАНУШЫ АҚПАРАТЫ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Username: {username_str}\n"
        f"🆔 Telegram ID: <code>{user.tg_id}</code>\n"
        f"📱 Телефон: <code>{phone_str}</code>\n\n"
        f"💳 Баланс: <b>{user.balance:,.0f} ₸</b>\n"
        f"🛒 Жалпы шыққын: <b>{user.total_spent:,.0f} ₸</b>\n"
        f"💰 Толтырылған: <b>{approved_payments:,.0f} ₸</b>\n"
        f"🔑 Кілттер: <b>{keys_count}</b>\n\n"
        f"🛡 Статус: {status_icon}\n"
        f"📅 Тіркелді: {user.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    await message.answer(text, parse_mode="HTML")
    await state.clear()
