from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from locales import get_text

# ─── CONTACT SHARE (first-time users) ────────────────────────────

def share_contact_keyboard(lang: str = "kk") -> ReplyKeyboardMarkup:
    """Keyboard with a request_contact button for identity verification."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(lang, "share_contact"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kk")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
        ]
    )

# ─── USER KEYBOARDS ───────────────────────────────────────────────

def main_menu_keyboard(lang: str = "kk") -> ReplyKeyboardMarkup:
    """Main dashboard keyboard with new features."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_products")), KeyboardButton(text=get_text(lang, "btn_topup"))],
            [KeyboardButton(text=get_text(lang, "btn_keys")),  KeyboardButton(text=get_text(lang, "btn_referral"))],
            [KeyboardButton(text=get_text(lang, "btn_support")), KeyboardButton(text=get_text(lang, "btn_promocode"))],
            [KeyboardButton(text=get_text(lang, "btn_profile")), KeyboardButton(text=get_text(lang, "btn_links"))],
            [KeyboardButton(text=get_text(lang, "btn_settings"))]
        ],
        resize_keyboard=True
    )


def products_keyboard(products, is_vip: bool = False, lang: str = "kk") -> InlineKeyboardMarkup:
    """One inline Buy button per product. Shows VIP price if applicable."""
    rows = []
    for p in products:
        if is_vip and getattr(p, 'vip_price', None) is not None:
            label = f"👑 {p.name} | 💸 {p.vip_price:,.0f} ₸ (VIP)"
        else:
            label = f"🛒 {p.name} | 💰 {p.price:,.0f} ₸"
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"buy_{p.id}"
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_to_menu_keyboard(lang: str = "kk") -> InlineKeyboardMarkup:
    """Back to menu button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_menu")]
        ]
    )

def admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Admin broadcast keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Send", callback_data="broadcast_send")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="broadcast_cancel")]
        ]
    )
