"""
Автоматты промокод жасау жүйесі (FSM)
Әкімші параметрлерді енгізіп, кездейсоқ промокодтарды автоматты түрде жасауы мүмкін.
"""

import logging
import random
import string
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.engine import async_session
from database.models import PromoCode
from config import config

router = Router()
log = logging.getLogger(__name__)


class AutoPromoStates(StatesGroup):
    """Автоматты промокод жасау үшін FSM күйлері."""
    waiting_for_count = State()
    waiting_for_amount = State()
    waiting_for_single_use = State()
    waiting_for_days = State()


def generate_promo_code(prefix: str = "PROMO", length: int = 8) -> str:
    """Кездейсоқ промокод жасау."""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}{random_part}"


@router.message(F.text == "🎟️ Автоматты промокод")
async def auto_promo_start(message: Message, state: FSMContext):
    """Автоматты промокод жасауды бастау."""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ Рұқсат жоқ.")
        return
    
    await message.answer(
        "🎟️ <b>АВТОМАТТЫ ПРОМОКОД ЖАСАУ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Әкімші панелі арқылы кездейсоқ промокодтарды жаппай жасаңыз.\n\n"
        "📊 <b>Қадам 1:</b> Қанша промокод жасағыңыз келеді?\n"
        "Мысалы: 10, 50, 100 т.б.\n\n"
        "Сандарды енгізіңіз:",
        parse_mode="HTML"
    )
    await state.set_state(AutoPromoStates.waiting_for_count)


@router.message(AutoPromoStates.waiting_for_count)
async def process_count(message: Message, state: FSMContext):
    """Промокод санын өңдеу."""
    try:
        count = int(message.text.strip())
        if count <= 0 or count > 1000:
            await message.answer("❌ 1 және 1000 арасында сан енгізіңіз.")
            return
        
        await state.update_data(count=count)
        await message.answer(
            "💰 <b>Қадам 2:</b> Әрбір промокодтың бонус сомасы\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Теңгемен енгізіңіз (мысалы: 100, 500, 1000)\n\n"
            "Сома:",
            parse_mode="HTML"
        )
        await state.set_state(AutoPromoStates.waiting_for_amount)
    except ValueError:
        await message.answer("❌ Дұрыс сан енгізіңіз. Мысалы: 10")


@router.message(AutoPromoStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    """Сомасын өңдеу."""
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сома 0-ден үлкен болуы керек.")
            return
        
        await state.update_data(amount=amount)
        await message.answer(
            "🔄 <b>Қадам 3:</b> Пайдалану түрі\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Бір реттік пайдалану ма?\n"
            "1 = Иә (бір реттік)\n"
            "0 = Жоқ (көп реттік)\n\n"
            "Таңдаңыз:",
            parse_mode="HTML"
        )
        await state.set_state(AutoPromoStates.waiting_for_single_use)
    except ValueError:
        await message.answer("❌ Дұрыс сан енгізіңіз. Мысалы: 100")


@router.message(AutoPromoStates.waiting_for_single_use)
async def process_single_use(message: Message, state: FSMContext):
    """Бір реттік пайдалану түрін өңдеу."""
    try:
        single_use = int(message.text.strip()) == 1
        await state.update_data(single_use=single_use)
        await message.answer(
            "⏰ <b>Қадам 4:</b> Жарамдылық мерзімі\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Қанша күн жарамды болсын?\n"
            "Мысалы: 30, 60, 90\n\n"
            "Күн санын енгізіңіз:",
            parse_mode="HTML"
        )
        await state.set_state(AutoPromoStates.waiting_for_days)
    except ValueError:
        await message.answer("❌ 0 немесе 1 енгізіңіз.")


@router.message(AutoPromoStates.waiting_for_days)
async def process_days(message: Message, state: FSMContext):
    """Мерзімін өңдеу және промокодтарды жасау."""
    try:
        days = int(message.text.strip())
        if days <= 0:
            await message.answer("❌ Күн саны 0-ден үлкен болуы керек.")
            return
        
        data = await state.get_data()
        count = data['count']
        amount = data['amount']
        single_use = data['single_use']
        
        # Статус хабарламасы
        await message.answer(
            f"⏳ Өңделіп тұр... {count} промокод жасалуда...",
            parse_mode="HTML"
        )
        
        # Промокодтарды жасау
        created_codes = []
        async with async_session() as session:
            for _ in range(count):
                # Бірегей код табу
                while True:
                    code = generate_promo_code()
                    existing = await session.scalar(
                        select(PromoCode).where(PromoCode.code == code)
                    )
                    if not existing:
                        break
                
                promo = PromoCode(
                    code=code,
                    bonus_amount=amount,
                    is_single_use=single_use,
                    is_active=True,
                    expires_at=datetime.utcnow() + timedelta(days=days)
                )
                session.add(promo)
                created_codes.append(code)
            
            await session.commit()
        
        # Нәтижені көрсету
        codes_text = "\n".join([f"  • {code}" for code in created_codes[:20]])
        if len(created_codes) > 20:
            codes_text += f"\n  ... және басқа {len(created_codes) - 20} код"
        
        await message.answer(
            f"✅ <b>ПРОМОКОДТАР СӘТТІ ЖАСАЛДЫ!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Параметрлер:</b>\n"
            f"   📌 Жасалған: <b>{count}</b> промокод\n"
            f"   💰 Әрбір сома: <b>{amount:,.0f} ₸</b>\n"
            f"   🔄 Түрі: <b>{'Бір реттік' if single_use else 'Көп реттік'}</b>\n"
            f"   ⏰ Мерзімі: <b>{days} күн</b>\n\n"
            f"<b>Жасалған кодтар:</b>\n"
            f"{codes_text}",
            parse_mode="HTML"
        )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Дұрыс сан енгізіңіз. Мысалы: 30")
