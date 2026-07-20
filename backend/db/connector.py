from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import cfg

engine = create_async_engine(cfg.postgres_url)

async_session = async_sessionmaker(engine, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session generator"""
    async with async_session() as session:
        yield session
