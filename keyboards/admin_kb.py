from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ─── ADMIN KEYBOARDS ─────────────────────────────────────────────

def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """Admin reply keyboard - Complete admin panel."""
    return ReplyKeyboardMarkup(
        keyboard=[
            # Кілттер (Keys)
            [KeyboardButton(text="🔑 1 КҮН"),  KeyboardButton(text="🔑 7 КҮН")],
            [KeyboardButton(text="🔑 15 КҮН"), KeyboardButton(text="🔑 30 КҮН")],
            [KeyboardButton(text="📂 Upload Keys (TXT)"),  KeyboardButton(text="📊 Statistics")],
            
            # Пайдаланушыларды басқару (User Management)
            [KeyboardButton(text="🚫 Ban User"),            KeyboardButton(text="💰 Add Balance")],
            [KeyboardButton(text="👁 User Info"),           KeyboardButton(text="🔙 User Mode")],
            
            # Тауарлар (Products)
            [KeyboardButton(text="➕ Тауар қосу"),          KeyboardButton(text="✏️ Баға өзгерту")],
            [KeyboardButton(text="🗑 Тауар жою")],
            
            # VIP жүйесі (VIP System)
            [KeyboardButton(text="🎖 VIP код жасау"),        KeyboardButton(text="👑 VIP клиенттер")],
            [KeyboardButton(text="🚫 VIP алып тастау")],
            
            # Промокодтар және Хабарламалар (New Features)
            [KeyboardButton(text="📋 Промокод тізімі"),      KeyboardButton(text="🎟️ Автоматты промокод")],
            [KeyboardButton(text="📢 Хабарлама жіберу")],
        ],
        resize_keyboard=True
    )

def approve_reject_keyboard(payment_id: int, user_tg_id: int) -> InlineKeyboardMarkup:
    """Inline Approve / Reject buttons sent to admin with receipt."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Approve",
                callback_data=f"pay_approve_{payment_id}_{user_tg_id}"
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"pay_reject_{payment_id}_{user_tg_id}"
            ),
        ]]
    )
