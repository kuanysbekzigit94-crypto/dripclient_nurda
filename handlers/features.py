"""
Жаңа функциялар үшін handlers:
- Промокодтар (Promo Codes)
- Қолдау (Support)
- Күнделікті бонус (Daily Bonus)
"""

import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.engine import async_session
from database.models import (
    User, PromoCode, PromoCodeUse, SupportTicket
)
from locales import get_text
from keyboards.user_kb import back_to_menu_keyboard

router = Router()
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# FSM STATES
# ═══════════════════════════════════════════════════════════════════════════════

class PromoCodeState(StatesGroup):
    waiting_for_code = State()

class SupportState(StatesGroup):
    waiting_for_message = State()

# ═══════════════════════════════════════════════════════════════════════════════
# ПРОМОКОДТАР (PROMO CODES)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🎟️ Промокод (Реферал)")
async def promo_code_start(message: Message, state: FSMContext):
    """Промокод енгізу процессін бастау."""
    user = await _get_user(message.from_user.id)
    if not user:
        return
    
    lang = user.language
    await state.set_state(PromoCodeState.waiting_for_code)
    await message.answer(
        get_text(lang, "promocode_title"),
        reply_markup=back_to_menu_keyboard(lang)
    )

@router.message(PromoCodeState.waiting_for_code)
async def apply_promo_code(message: Message, state: FSMContext):
    """Промокодты қолдану."""
    user = await _get_user(message.from_user.id)
    if not user:
        return
    
    lang = user.language
    code = message.text.strip().upper()
    
    # Кері қайту батырмасы
    if code == "◀️ BACK":
        await state.clear()
        await message.answer(get_text(lang, "dashboard_title"))
        return
    
    async with async_session() as session:
        # Промокодты табу
        promo = await session.scalar(
            select(PromoCode).where(PromoCode.code == code)
        )
        
        if not promo:
            await message.answer(get_text(lang, "promocode_invalid"))
            return
        
        # Промокодтың жарамдылығын тексеру
        if not promo.is_active:
            await message.answer(get_text(lang, "promocode_invalid"))
            return
        
        if promo.expires_at and promo.expires_at < datetime.utcnow():
            await message.answer(get_text(lang, "promocode_expired"))
            return
        
        if promo.max_uses and promo.used_count >= promo.max_uses:
            await message.answer(get_text(lang, "promocode_limit_reached"))
            return
        
        # Пайдаланушы бұрын бұл промокодты қолданған ма?
        if promo.is_single_use:
            existing_use = await session.scalar(
                select(PromoCodeUse).where(
                    (PromoCodeUse.promo_code_id == promo.id) &
                    (PromoCodeUse.user_tg_id == user.tg_id)
                )
            )
            if existing_use:
                await message.answer(get_text(lang, "promocode_invalid"))
                return
        
        # Бонусты есептеу
        bonus = 0
        if promo.bonus_amount:
            bonus = promo.bonus_amount
        elif promo.discount_percent:
            bonus = user.balance * (promo.discount_percent / 100)
        
        # Балансты өндіру
        user.balance += bonus
        
        # Промокодты пайдаланылған деп белгілеу
        promo.used_count += 1
        session.add(PromoCodeUse(
            promo_code_id=promo.id,
            user_tg_id=user.tg_id
        ))
        
        session.add(user)
        session.add(promo)
        await session.commit()
        
        await state.clear()
        await message.answer(
            get_text(lang, "promocode_success", bonus=bonus, balance=user.balance)
        )

# ═══════════════════════════════════════════════════════════════════════════════
# ҚОЛДАУ (SUPPORT)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(F.text.contains("💬"))
async def support_start(message: Message, state: FSMContext):
    """Қолдау сұрау процессін бастау."""
    user = await _get_user(message.from_user.id)
    if not user:
        return
    
    lang = user.language
    await state.set_state(SupportState.waiting_for_message)
    await message.answer(
        get_text(lang, "support_title"),
        reply_markup=back_to_menu_keyboard(lang)
    )

@router.message(SupportState.waiting_for_message)
async def submit_support_ticket(message: Message, state: FSMContext):
    """Қолдау сұрауын жіберу."""
    user = await _get_user(message.from_user.id)
    if not user:
        return
    
    lang = user.language
    
    # Кері қайту батырмасы
    if message.text == "◀️ Back":
        await state.clear()
        await message.answer(get_text(lang, "dashboard_title"))
        return
    
    async with async_session() as session:
        ticket = SupportTicket(
            user_tg_id=user.tg_id,
            message=message.text,
            status="open"
        )
        session.add(ticket)
        await session.commit()
        
        await state.clear()
        await message.answer(get_text(lang, "support_sent"))

# Күнделікті бонус функциясы алып тасталды

# ═══════════════════════════════════════════════════════════════════════════════
# КӨМЕКШІ ФУНКЦИЯЛАР
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_user(tg_id: int) -> User | None:
    """Пайдаланушыны табу."""
    async with async_session() as session:
        return await session.scalar(
            select(User).where(User.tg_id == tg_id)
        )
