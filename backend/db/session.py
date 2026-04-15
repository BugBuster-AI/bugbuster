from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import DB_URL
import json


def custom_serialize(value):
    # русские буквы пишутся норм, а не \u0430
    return json.dumps(value, ensure_ascii=False, indent=4)


def custom_deserialize(value):
    return json.loads(value)


# asyncpg + pgbouncer (transaction/statement): без кэша prepared statements.
engine = create_async_engine(
    DB_URL,
    future=True,
    echo=False,
    json_serializer=custom_serialize,
    json_deserializer=custom_deserialize,
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0},
)
async_session = sessionmaker(engine, expire_on_commit=False, autoflush=False, class_=AsyncSession, future=True)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session: AsyncSession = async_session()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def transaction_scope(session: AsyncSession):
    if session.in_transaction():
        yield
    else:
        async with session.begin():
            yield
