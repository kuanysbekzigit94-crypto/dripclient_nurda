"""
Әкімші функциялары:
- Промокодтарды басқару (Create, Edit, Delete)
- Хабарландырулар жіберу (Broadcast)
- Қолдау сұраулары (Support Tickets)
"""

import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.engine import async_session
from database.models import (
    User, PromoCode, SupportTicket, SupportReply
)
from locales import get_text
from config import config

router = Router()
log = logging.getLogger(__name__)


class BroadcastStates(StatesGroup):
    """Хабарлама жіберу үшін FSM күйлері."""
    waiting_for_message = State()


# ═══════════════════════════════════════════════════════════════════════════════
# ПРОМОКОДТАРДЫ БАСҚАРУ
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("promo_create"))
async def create_promo_code(message: Message):
    """Жаңа промокод құру. Пайдалану: /promo_create CODE 100 1 30"""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ Рұқсат жоқ.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 4:
            await message.answer(
                "❌ Қате формат.\n"
                "Пайдалану: /promo_create CODE AMOUNT SINGLE_USE(0/1) DAYS_VALID\n"
                "Мысалы: /promo_create WELCOME100 100 1 30"
            )
            return
        
        code = parts[1].upper()
        amount = float(parts[2])
        is_single = int(parts[3]) == 1
        days_valid = int(parts[4])
        
        async with async_session() as session:
            # Промокод бар ма?
            existing = await session.scalar(
                select(PromoCode).where(PromoCode.code == code)
            )
            if existing:
                await message.answer("❌ Бұл промокод бұрын бар.")
                return
            
            promo = PromoCode(
                code=code,
                bonus_amount=amount,
                is_single_use=is_single,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=days_valid)
            )
            session.add(promo)
            await session.commit()
            
            await message.answer(
                f"✅ Промокод құрылды!\n\n"
                f"📌 Код: {code}\n"
                f"💰 Сома: {amount} ₸\n"
                f"🔄 Түрі: {'Бір реттік' if is_single else 'Көп реттік'}\n"
                f"⏰ Әрекет ету: {days_valid} күн"
            )
    except Exception as e:
        log.error(f"Promo create error: {e}")
        await message.answer(f"❌ Қате: {e}")

@router.message(Command("promo_list"))
async def list_promo_codes(message: Message):
    """Барлық промокодтарды көрсету."""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ Рұқсат жоқ.")
        return
    
    async with async_session() as session:
        promos = (await session.execute(select(PromoCode))).scalars().all()
        
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
        
        await message.answer(text)

# ═══════════════════════════════════════════════════════════════════════════════
# ХАБАРЛАНДЫРУЛАР (BROADCAST) - НАҚТЫ ЖІБЕРУ
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "📢 Хабарлама жіберу")
async def broadcast_start(message: Message, state: FSMContext):
    """Хабарлама жіберу бастау."""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ Рұқсат жоқ.")
        return
    
    await message.answer(
        "📢 <b>ХАБАРЛАМА ЖІБЕРУ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Барлық пайдаланушыларға жіберілетін хабарлама мәтінін енгізіңіз:\n\n"
        "(HTML форматын қолдайды: <b>bold</b>, <i>italic</i>, <a href='url'>link</a>)",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_message)


@router.message(BroadcastStates.waiting_for_message)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    """Хабарламаны барлық пайдаланушыларға жіберу."""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ Рұқсат жоқ.")
        await state.clear()
        return
    
    broadcast_text = message.text
    
    try:
        # Статус хабарламасы
        status_msg = await message.answer(
            "⏳ Хабарлама жіберіліп тұр...",
            parse_mode="HTML"
        )
        
        async with async_session() as session:
            users = (await session.execute(select(User))).scalars().all()
            
            if not users:
                await message.answer("📭 Пайдаланушылар жоқ.")
                await state.clear()
                return
            
            sent_count = 0
            failed_count = 0
            
            # Хабарламаны барлық пайдаланушыларға жіберу
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.tg_id,
                        text=broadcast_text,
                        parse_mode="HTML"
                    )
                    sent_count += 1
                except Exception as e:
                    log.error(f"Broadcast error for user {user.tg_id}: {e}")
                    failed_count += 1
            
            # Нәтижені жаңарту
            await status_msg.edit_text(
                f"✅ <b>ХАБАРЛАМА ЖІБЕРІЛДІ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 Сәтті жіберілді: <b>{sent_count}</b>\n"
                f"❌ Сәтсіз: <b>{failed_count}</b>\n"
                f"📊 Барлығы: <b>{sent_count + failed_count}</b>",
                parse_mode="HTML"
            )
            
            await state.clear()
    except Exception as e:
        log.error(f"Broadcast error: {e}")
        await message.answer(f"❌ Қате: {e}")
        await state.clear()

# ═══════════════════════════════════════════════════════════════════════════════
# ҚОЛДАУ СҰРАУЛАРЫ (SUPPORT TICKETS)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("support_list"))
async def list_support_tickets(message: Message):
    """Ашық қолдау сұраулары."""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ Рұқсат жоқ.")
        return
    
    async with async_session() as session:
        tickets = (await session.execute(
            select(SupportTicket).where(SupportTicket.status == "open")
        )).scalars().all()
        
        if not tickets:
            await message.answer("📭 Ашық сұраулар жоқ.")
            return
        
        text = "💬 <b>АШЫҚ СҰРАУЛАР</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for t in tickets:
            text += (
                f"📌 <b>Сұрау #{t.id}</b>\n"
                f"   👤 Пайдаланушы: {t.user_tg_id}\n"
                f"   📝 Мәселе: {t.message[:50]}...\n"
                f"   📅 Түзетілген: {t.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
        
        await message.answer(text)

@router.message(Command("support_reply"))
async def reply_support_ticket(message: Message):
    """Қолдау сұрауына жауап беру. Пайдалану: /support_reply 1 Жауап мәтіні"""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ Рұқсат жоқ.")
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("❌ Қате формат.\nПайдалану: /support_reply TICKET_ID ЖАУАП_МӘТІНІ")
            return
        
        ticket_id = int(parts[1])
        reply_text = parts[2]
        
        async with async_session() as session:
            ticket = await session.get(SupportTicket, ticket_id)
            if not ticket:
                await message.answer("❌ Сұрау табылмады.")
                return
            
            reply = SupportReply(
                ticket_id=ticket_id,
                sender_tg_id=message.from_user.id,
                message=reply_text,
                is_from_admin=True
            )
            ticket.status = "in_progress"
            
            session.add(reply)
            session.add(ticket)
            await session.commit()
            
            await message.answer("✅ Жауап жіберілді!")
    except Exception as e:
        log.error(f"Support reply error: {e}")
        await message.answer(f"❌ Қате: {e}")
