from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Product, Key
from config import config

router = Router()


class AdminKeysState(StatesGroup):
    pasting_keys   = State()
    uploading_file = State()


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


async def _save_keys(db_session: AsyncSession, product_id: int, lines: list[str]) -> tuple[int, int]:
    added = skipped = 0
    for line in lines:
        val = line.strip()
        if not val:
            continue
        existing = await db_session.scalar(select(Key).where(Key.key_value == val))
        if not existing:
            db_session.add(Key(product_id=product_id, key_value=val))
            added += 1
        else:
            skipped += 1
    await db_session.commit()
    return added, skipped


# ─── DIRECT PRODUCT BUTTONS ──────────────────────────────────────
# These fire when admin taps the quick "🔑 Add: 1 КҮН" style buttons

PRODUCT_PREFIXES = {
    "🔑 1 КҮН":  "DRIP CLIENT (1 КҮН)",
    "🔑 7 КҮН":  "DRIP CLIENT (7 КҮН)",
    "🔑 15 КҮН": "DRIP CLIENT (15 КҮН)",
    "🔑 30 КҮН": "DRIP CLIENT (30 КҮН)",
}


@router.message(F.text.in_(PRODUCT_PREFIXES.keys()))
async def quick_add_keys(message: Message, state: FSMContext, db_user: User, db_session: AsyncSession):
    if not is_admin(db_user.tg_id):
        return

    product_name = PRODUCT_PREFIXES[message.text]
    product = await db_session.scalar(select(Product).where(Product.name == product_name))

    if not product:
        await message.answer(f"❌ «{product_name}» өнімі табылмады. seed.py іске қосыңыз.")
        return

    # Count remaining keys
    from sqlalchemy import func
    free = await db_session.scalar(
        select(func.count(Key.id)).where(Key.product_id == product.id, Key.is_used == False)
    ) or 0

    await state.set_state(AdminKeysState.pasting_keys)
    await state.update_data(product_id=product.id)
    await message.answer(
        f"🔑 <b>{product.name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Қалған кілт: <b>{free}</b>\n\n"
        f"Кілттерді жіберіңіз (әр кілт — жаңа жол):",
        parse_mode="HTML"
    )


@router.message(AdminKeysState.pasting_keys)
async def process_pasted_keys(message: Message, state: FSMContext, db_session: AsyncSession):
    if not message.text:
        await message.answer("⚠️ Мәтін жіберіңіз.")
        return
    data = await state.get_data()
    lines = message.text.split("\n")
    added, skipped = await _save_keys(db_session, data["product_id"], lines)
    await state.clear()
    await message.answer(
        f"✅ <b>Сәтті!</b>\n\n"
        f"➕ Қосылды: <b>{added}</b>\n"
        f"⏭ Қайталанған (өткізілді): {skipped}",
        parse_mode="HTML"
    )


# ─── TXT FILE UPLOAD (kept for convenience) ──────────────────────

@router.message(F.text == "📂 Upload Keys (TXT)")
async def upload_keys_handler(message: Message, state: FSMContext, db_user: User, db_session: AsyncSession):
    if not is_admin(db_user.tg_id):
        return

    result = await db_session.execute(select(Product))
    products = result.scalars().all()
    if not products:
        await message.answer("❌ Өнімдер жоқ.")
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from sqlalchemy import func
    rows = []
    for p in products:
        free = await db_session.scalar(
            select(func.count(Key.id)).where(Key.product_id == p.id, Key.is_used == False)
        ) or 0
        rows.append([InlineKeyboardButton(
            text=f"{p.name} | 🔑 {free}",
            callback_data=f"adm_file_{p.id}"
        )])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await state.update_data(next_step="file")
    await message.answer("📂 <b>Өнімді таңдаңыз:</b>", reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_file_"))
async def file_product_selected(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    product_id = int(callback.data.split("_")[2])
    prod = await db_session.scalar(select(Product).where(Product.id == product_id))
    if not prod:
        await callback.answer("Табылмады.", show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(AdminKeysState.uploading_file)
    await state.update_data(product_id=product_id)
    await callback.message.answer(
        f"✅ <b>{prod.name}</b> таңдалды.\n\n<b>.txt</b> файлын жіберіңіз:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminKeysState.uploading_file, F.document)
async def process_keys_file(message: Message, state: FSMContext, bot: Bot, db_session: AsyncSession):
    if not message.document.file_name.endswith('.txt'):
        await message.answer("⚠️ Тек .txt файлын жіберіңіз.")
        return
    data = await state.get_data()
    file_info = await bot.get_file(message.document.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    lines = downloaded.read().decode('utf-8').splitlines()
    added, skipped = await _save_keys(db_session, data["product_id"], lines)
    await state.clear()
    await message.answer(
        f"✅ <b>Файлдан кілттер жүктелді!</b>\n\n➕ Жаңа: <b>{added}</b>\n⏭ Қайталанған: {skipped}",
        parse_mode="HTML"
    )


@router.message(AdminKeysState.uploading_file)
async def uploading_wrong_type(message: Message):
    await message.answer("⚠️ .txt файлын жіберіңіз.")
