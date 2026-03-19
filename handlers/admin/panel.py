from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import User, Payment, Purchase, Key, PromoCode
from config import config
from keyboards.admin_kb import admin_panel_keyboard
from keyboards.user_kb import main_menu_keyboard

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("admin"))
async def admin_start(message: Message, db_user: User):
    if not is_admin(db_user.tg_id):
        await message.answer("⛔ Рұқсат жоқ.")
        return

    await message.answer(
        "🔧 <b>ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 @{message.from_user.username}\n"
        f"Admin IDs: {config.admin_ids}",
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔙 User Mode")
async def user_mode_handler(message: Message, db_user: User):
    if not is_admin(db_user.tg_id):
        return
    await message.answer("↩️ Пайдаланушы режиміне өттіңіз.", reply_markup=main_menu_keyboard())


@router.message(F.text == "📊 Statistics")
async def admin_stats_handler(message: Message, db_session: AsyncSession, db_user: User):
    if not is_admin(db_user.tg_id):
        return

    users_count = await db_session.scalar(select(func.count(User.id)))
    keys_total  = await db_session.scalar(select(func.count(Key.id))) or 0
    keys_used   = await db_session.scalar(select(func.count(Key.id)).where(Key.is_used == True)) or 0
    keys_free   = keys_total - keys_used
    total_sales = await db_session.scalar(select(func.sum(Purchase.price))) or 0
    total_paid  = await db_session.scalar(select(func.sum(Payment.amount)).where(Payment.status == "approved")) or 0
    pending_cnt = await db_session.scalar(select(func.count(Payment.id)).where(Payment.status == "pending")) or 0

    text = (
        f"📊 <b>СТАТИСТИКА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Пайдаланушылар: <b>{users_count}</b>\n\n"
        f"🔑 Кілттер барлығы: <b>{keys_total}</b>\n"
        f"   ✅ Пайдаланылған: {keys_used}\n"
        f"   🟡 Қалған:        {keys_free}\n\n"
        f"💰 Жалпы сатылым:     <b>{total_sales:,.0f} ₸</b>\n"
        f"💳 Бекітілген төлем:  <b>{total_paid:,.0f} ₸</b>\n"
        f"⏳ Күтіп тұрған:      <b>{pending_cnt}</b>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📋 Промокод тізімі")
async def promo_list_handler(message: Message, db_session: AsyncSession, db_user: User):
    if not is_admin(db_user.tg_id):
        return
    
    promos = (await db_session.execute(select(PromoCode))).scalars().all()
    
    if not promos:
        await message.answer("📭 Промокодтар жоқ.")
        return
    
    text = "🎟️ <b>ПРОМОКОДТАР ТІЗІМІ</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for p in promos:
        status = "✅ Белсенді" if p.is_active else "❌ Өшіктік"
        expires = p.expires_at.strftime("%Y-%m-%d") if p.expires_at else "Шектеусіз"
        text += (
            f"📌 <b>{p.code}</b>\n"
            f"   💰 Сома: {p.bonus_amount} ₸\n"
            f"   🔄 Пайдалану: {p.used_count}\n"
            f"   🔮 Күй: {status}\n"
            f"   ⏰ Мерзімі: {expires}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")
