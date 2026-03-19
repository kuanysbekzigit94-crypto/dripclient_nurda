import asyncio
from sqlalchemy import select

# Import ALL models so Base.metadata knows about every table
import database.models  # noqa: F401
from database.engine import async_session, create_db
from database.models import Product

PRODUCTS = [
    {"name": "1 КҮН",  "price": 366.0,  "description": "1 күндік лицензия"},
    {"name": "7 КҮН",  "price": 2555.0, "description": "7 күндік лицензия"},
    {"name": "15 КҮН", "price": 3333.0, "description": "15 күндік лицензия"},
    {"name": "30 КҮН", "price": 5555.0, "description": "30 күндік лицензия"},
]

async def seed():
    # Create all tables if they don't exist yet
    await create_db()

    async with async_session() as session:
        inserted = 0
        for data in PRODUCTS:
            result = await session.execute(
                select(Product).where(Product.name == data["name"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"[SKIP]   '{data['name']}' already exists (id={existing.id})")
            else:
                product = Product(
                    name=data["name"],
                    price=data["price"],
                    description=data["description"],
                )
                session.add(product)
                inserted += 1
                print(f"[INSERT] '{data['name']}' — {data['price']} ₸")

        await session.commit()
        print(f"\nDone. {inserted} product(s) inserted, {len(PRODUCTS) - inserted} skipped.")

if __name__ == "__main__":
    asyncio.run(seed())
