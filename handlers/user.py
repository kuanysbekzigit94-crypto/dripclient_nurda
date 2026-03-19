from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Product, Key
from keyboards.user_kb import main_menu_keyboard, products_keyboard
from locales import get_text, get_all_translations

router = Router()


# ─── PRODUCTS ────────────────────────────────────────────────────

@router.message(F.text.in_(get_all_translations("btn_products")))
async def products_handler(message: Message, db_user: User, db_session: AsyncSession):
    result = await db_session.execute(select(Product))
    products = result.scalars().all()

    if not products:
        await message.answer(get_text(db_user.language, "products_empty"))
        return

    title = get_text(db_user.language, "products_title")
    vip_text = get_text(db_user.language, "vip_price_active") if db_user.is_vip else ""
    bal_text = get_text(db_user.language, "balance")

    text = (
        f"{title}\n\n"
        f"{vip_text}\n"
        f"{bal_text}: <b>{db_user.balance:,.0f} ₸</b>"
    )
    await message.answer(
        text,
        reply_markup=products_keyboard(products, is_vip=db_user.is_vip, lang=db_user.language),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("buy_"))
async def buy_product_cb(callback: CallbackQuery, db_user: User, db_session: AsyncSession):
    product_id = int(callback.data.split("_")[1])

    from services.key_allocator import process_purchase
    success, msg = await process_purchase(db_session, db_user, product_id)

    if success:
        success_text = get_text(db_user.language, "buy_success", msg=msg, balance=db_user.balance)
        await callback.message.answer(
            success_text,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(db_user.language)
        )
    else:
        await callback.answer(f"❌ {msg}", show_alert=True)

    await callback.answer()


# ─── MY KEYS ─────────────────────────────────────────────────────

@router.message(F.text.in_(get_all_translations("btn_keys")))
async def my_keys_handler(message: Message, db_user: User, db_session: AsyncSession):
    result = await db_session.execute(
        select(Key).join(Product)
        .where(Key.used_by == db_user.tg_id)
        .order_by(Key.created_at.desc())
    )
    keys = result.scalars().all()

    if not keys:
        await message.answer(get_text(db_user.language, "keys_empty"))
        return

    title = get_text(db_user.language, "keys_title")
    text = f"{title}\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for key in keys:
        text += f"📦 <b>{key.product.name}</b>\n<code>{key.key_value}</code>\n\n"

    await message.answer(text, parse_mode="HTML")
