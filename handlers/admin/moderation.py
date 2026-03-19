from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Payment
from config import config
from database.github_sync import save_database
import asyncio

router = Router()


@router.callback_query(F.data.startswith("pay_approve_"))
async def approve_payment_cb(callback: CallbackQuery, db_session: AsyncSession, bot: Bot):
    if callback.from_user.id not in config.admin_ids:
        await callback.answer("⛔ Рұқсат жоқ!", show_alert=True)
        return

    _, _, payment_id, user_tg_id = callback.data.split("_", 3)
    payment_id, user_tg_id = int(payment_id), int(user_tg_id)

    payment = await db_session.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        await callback.answer("Төлем табылмады.", show_alert=True)
        return
    if payment.status != "pending":
        await callback.answer(f"Төлем бұрын өңделді: {payment.status}", show_alert=True)
        return

    user = await db_session.scalar(select(User).where(User.tg_id == user_tg_id))
    if not user:
        await callback.answer("Пайдаланушы табылмады.", show_alert=True)
        return

    payment.status = "approved"
    user.balance += payment.amount
    await db_session.commit()
    asyncio.create_task(save_database())

    # Update admin message
    new_caption = (
        callback.message.caption + "\n\n"
        f"✅ <b>МАҚҰЛДАНДЫ</b> — @{callback.from_user.username or callback.from_user.id}"
    )
    await callback.message.edit_caption(caption=new_caption, reply_markup=None, parse_mode="HTML")

    # Notify user
    try:
        await bot.send_message(
            chat_id=user_tg_id,
            text=(
                f"✅ <b>Төлем мақұлданды!</b>\n\n"
                f"💰 <b>{payment.amount:,.0f} ₸</b> балансыңызға қосылды.\n"
                f"Жаңа баланс: <b>{user.balance:,.0f} ₸</b>"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("✅ Мақұлданды!")


@router.callback_query(F.data.startswith("pay_reject_"))
async def reject_payment_cb(callback: CallbackQuery, db_session: AsyncSession, bot: Bot):
    if callback.from_user.id not in config.admin_ids:
        await callback.answer("⛔ Рұқсат жоқ!", show_alert=True)
        return

    _, _, payment_id, user_tg_id = callback.data.split("_", 3)
    payment_id, user_tg_id = int(payment_id), int(user_tg_id)

    payment = await db_session.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        await callback.answer("Төлем табылмады.", show_alert=True)
        return
    if payment.status != "pending":
        await callback.answer(f"Төлем бұрын өңделді: {payment.status}", show_alert=True)
        return

    payment.status = "rejected"
    await db_session.commit()

    new_caption = (
        callback.message.caption + "\n\n"
        f"❌ <b>ҚАБЫЛДАНБАДЫ</b> — @{callback.from_user.username or callback.from_user.id}"
    )
    await callback.message.edit_caption(caption=new_caption, reply_markup=None, parse_mode="HTML")

    try:
        await bot.send_message(
            chat_id=user_tg_id,
            text=(
                f"❌ <b>Төлеміңіз қабылданбады.</b>\n\n"
                f"Сома: <b>{payment.amount:,.0f} ₸</b>\n\n"
                f"Сұрақ болса, админге хабарласыңыз."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("❌ Қабылданбады!")
