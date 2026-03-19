import secrets
import string

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import User, VipCode
from handlers.admin.panel import is_admin

router = Router()

# ─── FSM ─────────────────────────────────────────────────────────────────────

class VipAdminFSM(StatesGroup):
    waiting_count       = State()   # how many codes to generate
    waiting_remove_id   = State()   # tg_id to remove VIP from


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _generate_code() -> str:
    """Generate a secure VIP code like VIP-A7K92L"""
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
    return f"VIP-{suffix}"


# ══════════════════════════════════════════════════════════════════════════════
# CREATE VIP CODES
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🎖 VIP код жасау")
async def vip_create_start(message: Message, db_user: User, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return
    await state.set_state(VipAdminFSM.waiting_count)
    await message.answer(
        "🎖 <b>VIP код жасау</b>\n\n"
        "Қанша код жасау керек?\n"
        "<i>(мысалы: 5)</i>",
        parse_mode="HTML"
    )


@router.message(VipAdminFSM.waiting_count)
async def vip_create_generate(message: Message, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return
    try:
        count = int(message.text.strip())
        if count < 1 or count > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ 1 мен 100 аралығында сан енгізіңіз.")
        return

    codes = []
    for _ in range(count):
        while True:
            code = _generate_code()
            exists = await db_session.scalar(select(VipCode).where(VipCode.code == code))
            if not exists:
                break
        vip_code = VipCode(code=code)
        db_session.add(vip_code)
        codes.append(code)

    await db_session.commit()
    await state.clear()

    codes_text = "\n".join(f"<code>{c}</code>" for c in codes)
    await message.answer(
        f"✅ <b>{count} VIP код жасалды:</b>\n\n{codes_text}",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════════════════════
# VIEW VIP CLIENTS
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "👑 VIP клиенттер")
async def vip_list(message: Message, db_user: User, db_session: AsyncSession):
    if not is_admin(db_user.tg_id):
        return

    result = await db_session.execute(
        select(User).where(User.is_vip == True).order_by(User.created_at.desc())
    )
    vip_users = result.scalars().all()

    if not vip_users:
        await message.answer("👑 VIP клиенттер жоқ.")
        return

    # Count unused codes
    unused_count = await db_session.scalar(
        select(func.count(VipCode.id)).where(VipCode.is_used == False)
    ) or 0

    text = (
        f"👑 <b>VIP КЛИЕНТТЕР</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Жалпы: <b>{len(vip_users)}</b>  |  Қолданылмаған кодтар: <b>{unused_count}</b>\n\n"
    )
    for u in vip_users:
        uname = f"@{u.username}" if u.username else "—"
        text += f"⭐ <b>{uname}</b> | ID: <code>{u.tg_id}</code>\n"

    await message.answer(text, parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════════════════
# REMOVE VIP STATUS
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🚫 VIP алып тастау")
async def vip_remove_start(message: Message, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    result = await db_session.execute(
        select(User).where(User.is_vip == True).order_by(User.created_at.desc())
    )
    vip_users = result.scalars().all()

    if not vip_users:
        await message.answer("👑 VIP клиенттер жоқ.")
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"{'@'+u.username if u.username else 'ID:'+str(u.tg_id)}",
            callback_data=f"vip_remove:{u.tg_id}"
        )]
        for u in vip_users
    ]
    buttons.append([InlineKeyboardButton(text="❌ Болдырмау", callback_data="vip_cancel")])

    await state.set_state(VipAdminFSM.waiting_remove_id)
    await message.answer(
        "🚫 <b>VIP мәртебесін алып тастау</b>\n\nПайдаланушыны таңдаңыз:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("vip_remove:"), VipAdminFSM.waiting_remove_id)
async def vip_remove_confirm(callback: CallbackQuery, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    tg_id = int(callback.data.split(":")[1])
    target = await db_session.scalar(select(User).where(User.tg_id == tg_id))

    if not target or not target.is_vip:
        await callback.answer("Пайдаланушы табылмады немесе VIP емес.", show_alert=True)
        await state.clear()
        return

    target.is_vip = False

    # Also free their VIP code so it can't be reused by them again (keep it as used)
    await db_session.commit()
    await state.clear()

    uname = f"@{target.username}" if target.username else str(tg_id)
    await callback.message.edit_text(
        f"✅ <b>{uname}</b> пайдаланушысының VIP мәртебесі алынды.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "vip_cancel")
async def vip_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Болдырылмады.")
    await callback.answer()
