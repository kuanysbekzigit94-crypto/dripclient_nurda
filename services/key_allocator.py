import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Product, Key, Purchase
from database.github_sync import save_database

def get_effective_price(product: Product, user: User) -> float:
    """Return VIP-discounted price if applicable."""
    if user.is_vip and product.vip_price is not None:
        return product.vip_price
    return product.price


async def process_purchase(session: AsyncSession, user: User, product_id: int) -> tuple[bool, str]:
    """
    Business logic for purchasing a product.
    Returns (success: bool, message: str)
    """
    # 1. Check Product exists
    product_result = await session.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()

    if not product:
        return False, "Product not found."

    # 2. Determine effective price (VIP discount)
    effective_price = get_effective_price(product, user)

    # 3. Check balance
    if user.balance < effective_price:
        return False, "Insufficient balance. Please top-up."

    # 4. Find available key
    key_result = await session.execute(
        select(Key).where(Key.product_id == product_id, Key.is_used == False).with_for_update().limit(1)
    )
    key = key_result.scalar_one_or_none()

    if not key:
        return False, "No available keys for this product."

    # 5. Deduct balance and total_spent
    user.balance     -= effective_price
    user.total_spent += effective_price

    # 6. Mark key as used
    key.is_used = True
    key.used_by = user.tg_id

    # 7. Record purchase
    purchase = Purchase(
        user_tg_id=user.tg_id,
        product_id=product_id,
        key_id=key.id,
        price=effective_price
    )
    session.add(purchase)

    # Commit changes
    await session.commit()

    # Persist to GitHub (fire-and-forget)
    asyncio.create_task(save_database())

    vip_note = " (VIP жеңілдік)" if user.is_vip else ""
    return True, (
        f"Here is your key for {product.name}:\n"
        f"<code>{key.key_value}</code>\n\n"
        f"💰 Төлем: <b>{effective_price:,.0f} ₸</b>{vip_note}"
    )
