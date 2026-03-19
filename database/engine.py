from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from config import config

engine = create_async_engine(config.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
