import os

from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

load_dotenv()

postgres_url = URL.create(
    "postgresql+asyncpg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host=os.environ.get("POSTGRES_HOST", "db"),
    port=int(os.environ.get("POSTGRES_PORT", "5432")),
    database=os.environ["POSTGRES_DB"],
)

# Streamlit часто создаёт новый event loop через asyncio.run. NullPool не даёт
# asyncpg-соединению из старого loop повторно использоваться в новом.
engine = create_async_engine(postgres_url, poolclass=NullPool)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
