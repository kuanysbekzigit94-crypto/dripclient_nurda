import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database.models import User, Product
from handlers.admin.panel import is_admin
from database.github_sync import save_database

router = Router()


# ─── FSM States ──────────────────────────────────────────────────────────────

class AddProductFSM(StatesGroup):
    waiting_name  = State()
    waiting_price = State()
    waiting_vip_price = State()

class EditPriceFSM(StatesGroup):
    waiting_product = State()   # callback triggers this
    waiting_price_type = State()
    waiting_price   = State()

class DeleteProductFSM(StatesGroup):
    waiting_confirm = State()   # expects callback confirm/cancel


# ─── Helper: inline keyboard of all products ─────────────────────────────────

def products_inline_kb(products: list[Product], action: str) -> InlineKeyboardMarkup:
    """action = 'edit_price' | 'delete_product'"""
    buttons = [
        [InlineKeyboardButton(
            text=f"{p.name} — {p.price:,.0f} ₸",
            callback_data=f"{action}:{p.id}"
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton(text="❌ Болдырмау", callback_data="product_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delete_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for product deletion."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Иә, жою", callback_data=f"delete_confirm:{product_id}"),
                InlineKeyboardButton(text="↩️ Болдырмау", callback_data="product_cancel"),
            ]
        ]
    )


# ══════════════════════════════════════════════════════════════════════════════
# ADD PRODUCT
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "➕ Тауар қосу")
async def add_product_start(message: Message, db_user: User, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return
    await state.set_state(AddProductFSM.waiting_name)
    await message.answer(
        "📦 <b>Жаңа тауар қосу</b>\n\n"
        "Тауардың атын жазыңыз:\n"
        "<i>(мысалы: 1 КҮН)</i>",
        parse_mode="HTML"
    )


@router.message(AddProductFSM.waiting_name)
async def add_product_name(message: Message, db_user: User, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProductFSM.waiting_price)
    await message.answer(
        f"✅ Атауы: <b>{message.text.strip()}</b>\n\n"
        "Бағасын теңгемен енгізіңіз:\n"
        "<i>(мысалы: 366)</i>",
        parse_mode="HTML"
    )


@router.message(AddProductFSM.waiting_price)
async def add_product_price(message: Message, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    try:
        price = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Дұрыс сан енгізіңіз, мысалы: <b>366</b>", parse_mode="HTML")
        return

    await state.update_data(price=price)
    await state.set_state(AddProductFSM.waiting_vip_price)
    await message.answer(
        f"✅ Қалыпты баға: <b>{price:,.0f} ₸</b>\n\n"
        "Енді VIP жазылушыларына арналған бағаны енгізіңіз\n"
        "<i>(Егер VIP жеңілдік болмаса 0 деп жазыңыз)</i>:",
        parse_mode="HTML"
    )

@router.message(AddProductFSM.waiting_vip_price)
async def add_product_vip_price(message: Message, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    try:
        vip_price = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Дұрыс сан енгізіңіз, мысалы: <b>200</b>", parse_mode="HTML")
        return

    if vip_price <= 0:
        vip_price = None

    data = await state.get_data()
    name = data["name"]
    price = data["price"]

    # Check duplicate
    existing = await db_session.scalar(select(Product).where(Product.name == name))
    if existing:
        await state.clear()
        await message.answer(
            f"⚠️ <b>{name}</b> атты тауар бұрыннан бар!\n"
            "Бағасын өзгерту үшін «✏️ Баға өзгерту» батырмасын қолданыңыз.",
            parse_mode="HTML"
        )
        return

    product = Product(name=name, price=price, vip_price=vip_price, description=f"{name} лицензиясы")
    db_session.add(product)
    await db_session.commit()
    await state.clear()

    # Save to Github Sync immediately
    asyncio.create_task(save_database())

    vp_str = f"{vip_price:,.0f} ₸" if vip_price else "Жоқ"
    await message.answer(
        f"✅ <b>Тауар сәтті қосылды!</b>\n\n"
        f"📦 Атауы: <b>{name}</b>\n"
        f"💰 Бағасы: <b>{price:,.0f} ₸</b>\n"
        f"💎 VIP баға: <b>{vp_str}</b>",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════════════════════
# EDIT PRODUCT PRICE
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "✏️ Баға өзгерту")
async def edit_price_start(message: Message, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    result = await db_session.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()

    if not products:
        await message.answer("⚠️ Тауарлар жоқ.")
        return

    await state.set_state(EditPriceFSM.waiting_product)
    await message.answer(
        "✏️ <b>Бағасын өзгерту</b>\n\n"
        "Тауарды таңдаңыз:",
        reply_markup=products_inline_kb(products, "edit_price"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_price:"), EditPriceFSM.waiting_product)
async def edit_price_chosen(callback: CallbackQuery, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    product_id = int(callback.data.split(":")[1])
    product = await db_session.get(Product, product_id)
    if not product:
        await callback.answer("Тауар табылмады.", show_alert=True)
        return

    await state.update_data(product_id=product_id, product_name=product.name)
    await state.set_state(EditPriceFSM.waiting_price_type)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Қалыпты баға", callback_data="price_type:normal"),
         InlineKeyboardButton(text="💎 VIP баға", callback_data="price_type:vip")],
        [InlineKeyboardButton(text="❌ Болдырмау", callback_data="product_cancel")]
    ])
    
    vp_str = f"{product.vip_price:,.0f} ₸" if product.vip_price else "Жоқ"
    await callback.message.edit_text(
        f"✏️ <b>{product.name}</b>\n\n"
        f"Қалыпты баға: <b>{product.price:,.0f} ₸</b>\n"
        f"VIP баға: <b>{vp_str}</b>\n\n"
        "Қай бағаны өзгерткіңіз келеді?",
        reply_markup=markup,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("price_type:"), EditPriceFSM.waiting_price_type)
async def edit_price_type_chosen(callback: CallbackQuery, state: FSMContext):
    p_type = callback.data.split(":")[1]
    await state.update_data(price_type=p_type)
    await state.set_state(EditPriceFSM.waiting_price)
    
    type_str = "ҚАЛЫПТЫ" if p_type == "normal" else "VIP"
    hint_str = "2555" if p_type == "normal" else "200 (VIP жою үшін 0 жазыңыз)"
    
    await callback.message.edit_text(
        f"✏️ Жаңа <b>{type_str}</b> бағаны теңгемен енгізіңіз:\n<i>(Мысалы: {hint_str})</i>", 
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditPriceFSM.waiting_price)
async def edit_price_confirm(message: Message, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    try:
        new_price = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Дұрыс сан енгізіңіз.", parse_mode="HTML")
        return

    data = await state.get_data()
    product = await db_session.get(Product, data["product_id"])
    p_type = data["price_type"]

    if p_type == "normal":
        product.price = new_price
        msg = f"Қалыпты баға <b>{new_price:,.0f} ₸</b> болып өзгертілді"
    else:
        product.vip_price = new_price if new_price > 0 else None
        msg = f"VIP баға <b>{new_price:,.0f} ₸</b> болып өзгертілді" if new_price > 0 else "VIP баға жойылды"

    await db_session.commit()
    await state.clear()
    
    asyncio.create_task(save_database())

    await message.answer(
        f"✅ <b>Сәтті сақталды!</b>\n\n"
        f"📦 Тауар: <b>{product.name}</b>\n"
        f"ℹ️ {msg}",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════
# DELETE PRODUCT
# ═══════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🗑 Тауар жою")
async def delete_product_start(message: Message, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    from sqlalchemy import func
    from database.models import Key

    result = await db_session.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()

    if not products:
        await message.answer("⚠️ Жойылатын тауар жоқ.")
        return

    # Show each product with its free/used key count
    lines = []
    for p in products:
        total = await db_session.scalar(select(func.count(Key.id)).where(Key.product_id == p.id)) or 0
        used  = await db_session.scalar(select(func.count(Key.id)).where(Key.product_id == p.id, Key.is_used == True)) or 0
        lines.append(f"• {p.name} | 💰{p.price:,.0f}₸ | 🔑{total} (✅{used} пайдаланылған)")

    await state.set_state(DeleteProductFSM.waiting_confirm)
    await message.answer(
        "🗑 <b>Тауар жою</b>\n\n"
        "<b>Қол жетімді тауарлар:</b>\n" + "\n".join(lines) + "\n\n"
        "⚠️ <i>Жою кезінде тауардың <b>бос (сатылмаған) кілттері</b> жойылады.</i>\n"
        "✅ <i>Сатып алынған кілттер сақталады (пайдаланушылар оларды көре ала алады).</i>\n"
        "Қай тауарды жойғыңыз келеді?",
        reply_markup=products_inline_kb(products, "delete_product"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("delete_product:"), DeleteProductFSM.waiting_confirm)
async def delete_product_chosen(callback: CallbackQuery, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        return

    from sqlalchemy import func
    from database.models import Key

    product_id = int(callback.data.split(":")[1])
    product = await db_session.get(Product, product_id)
    if not product:
        await callback.answer("Тауар табылмады.", show_alert=True)
        await state.clear()
        return

    # Count keys
    total_keys = await db_session.scalar(select(func.count(Key.id)).where(Key.product_id == product_id)) or 0
    used_keys  = await db_session.scalar(select(func.count(Key.id)).where(Key.product_id == product_id, Key.is_used == True)) or 0
    free_keys  = total_keys - used_keys

    await callback.message.edit_text(
        f"⚠️ <b>Растаңыз: Тауар жою</b>\n\n"
        f"📦 Тауар: <b>{product.name}</b>\n"
        f"💰 Баға: <b>{product.price:,.0f} ₸</b>\n\n"
        f"🔑 Барлық кілт: <b>{total_keys}</b>\n"
        f"   🗑 Бос (<b>жойылады</b>): <b>{free_keys}</b>\n"
        f"   ✅ Сатып алынған (<b>сақталады</b>): <b>{used_keys}</b>\n\n"
        f"💡 <i>Тек сатылмаған (бос) {free_keys} кілт жойылады.\n"
        f"Сатып алынған {used_keys} кілт пайдаланушыларда сақталады.</i>\n\n"
        f"<b>Жалғастырасыз ба?</b>",
        reply_markup=delete_confirm_kb(product_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def delete_product_confirmed(callback: CallbackQuery, db_user: User, db_session: AsyncSession, state: FSMContext):
    if not is_admin(db_user.tg_id):
        await callback.answer("⛔ Рұқсат жоқ!", show_alert=True)
        return

    from database.models import Key

    product_id = int(callback.data.split(":")[1])
    product = await db_session.get(Product, product_id)
    if not product:
        await callback.answer("Тауар табылмады.", show_alert=True)
        await state.clear()
        return

    product_name = product.name

    # Delete free (unused) keys first
    free_deleted = await db_session.execute(
        delete(Key).where(Key.product_id == product_id, Key.is_used == False)
    )
    free_count = free_deleted.rowcount

    # Delete the product itself (used keys will have product_id set by FK, safe to keep for history)
    await db_session.delete(product)
    await db_session.commit()
    await state.clear()

    asyncio.create_task(save_database())

    await callback.message.edit_text(
        f"✅ <b>Тауар сәтті жойылды!</b>\n\n"
        f"📦 Жойылған тауар: <b>{product_name}</b>\n"
        f"🗑 Жойылған бос кілттер: <b>{free_count}</b>\n\n"
        f"✅ <i>Сатып алынған кілттер сақталған. Пайдаланушылар оларды жарнамайды.</i>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Жойылды!")


# ─── Cancel ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "product_cancel")
async def product_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Болдырылмады.")
    await callback.answer()
