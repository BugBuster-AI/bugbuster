import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    FLOAT,
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    create_engine,
    func,
    null,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.celeryconfig import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from core.schemas import CaseStatusEnum


def custom_serialize(value):
    return json.dumps(value, ensure_ascii=False, indent=4)


def custom_deserialize(value):
    return json.loads(value)


DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async_engine = create_async_engine(DB_URL, future=True, echo=False,
                                   json_serializer=custom_serialize, json_deserializer=custom_deserialize,
                                   pool_pre_ping=True,
                                   pool_recycle=1800,
                                   pool_timeout=30,
                                   max_overflow=20,
                                   connect_args={"statement_cache_size": 0})
async_session = sessionmaker(async_engine, expire_on_commit=True, autoflush=False, class_=AsyncSession, future=True)

sync_engine = create_engine(DB_URL.replace("asyncpg", "psycopg2"), future=True, echo=False,
                            json_serializer=custom_serialize, json_deserializer=custom_deserialize)
sync_session = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False, class_=Session)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def check_run_case_status(run_id) -> bool:
    # если вдруг статус в БД уже конечный, задачу делать не надо
    async with async_session() as session:
        async with session.begin():
            query = await session.execute(select(RunCase)
                                          .where(RunCase.run_id == run_id))
            run_case: RunCase = query.scalars().one_or_none()

            if not run_case:
                return False
            # в принципе он должен быть только в CaseStatusEnum.PREPARATION
            # это когда паблишер из очереди перевел его на выполнение и отправил в rabbit
            # но на всякий
            if run_case.status not in (CaseStatusEnum.IN_PROGRESS,
                                       CaseStatusEnum.PREPARATION,
                                       CaseStatusEnum.IN_QUEUE,
                                       CaseStatusEnum.STOP_IN_PROGRESS):
                return False
            return True


async def get_user_host(user_id, session=None) -> str:

    query = select(User.host).where(User.user_id == user_id)
    host = ""
    if session is None:
        async with async_session() as session:
            async with session.begin():
                res = await session.execute(query)
                host = res.scalar_one_or_none() or ""
    else:
        async with session.begin():
            res = await session.execute(query)
            host = res.scalar_one_or_none() or ""
    return host


async def update_run_case_status(run_id, status, run_summary: str = None,
                                 start_dt=None, end_dt=None, complete_time=None, session=None):

    values = {'status': status}
    if run_summary is not None:
        values['run_summary'] = str(run_summary)
    if start_dt is not None:
        values['start_dt'] = start_dt
    if end_dt is not None:
        values['end_dt'] = end_dt
    if complete_time is not None:
        values['complete_time'] = complete_time

    query = update(RunCase).where(RunCase.run_id == run_id).values(**values)

    if session is None:
        async with async_session() as session:
            async with session.begin():
                await session.execute(query)
    else:
        async with session.begin():
            await session.execute(query)


async def update_run_case_stop(run_id, start_dt, session=None):
    query = update(RunCase).where(RunCase.run_id == run_id).values(status=CaseStatusEnum.STOPPED,
                                                                   start_dt=start_dt,
                                                                   end_dt=datetime.now(timezone.utc),
                                                                   complete_time=(datetime.now(timezone.utc) - start_dt).total_seconds())

    if session is None:
        async with async_session() as session:
            async with session.begin():
                await session.execute(query)

    else:
        async with session.begin():
            await session.execute(query)


async def update_run_case_final_record(run_id, video, end_dt, complete_time, status, run_summary, session=None):

    query = (
        update(RunCase)
        .where(RunCase.run_id == run_id)
        .values(
            video=video if video is not None else null(),
            end_dt=end_dt,
            complete_time=complete_time,
            status=status,
            run_summary=run_summary
        )
    )
    if session is None:
        async with async_session() as session:
            async with session.begin():
                await session.execute(query)
    else:
        async with session.begin():
            await session.execute(query)


async def update_run_case_steps(session, run_id, step_data):
    # result = await session.execute(
    #     select(RunCase.steps).where(RunCase.run_id == run_id)
    # )
    # current_steps = result.scalar() or []
    # current_steps.append(step_data)
    # query = update(RunCase).where(RunCase.run_id == run_id).values(steps=current_steps)
    # await session.execute(query)
    # await session.commit()

    # все шаги теперь есть заранее для фронта, обновляем по ходу выполнения
    async with session.begin():
        result = await session.execute(
            select(RunCase.steps).where(RunCase.run_id == run_id)
        )
        current_steps = result.scalar() or []

        # Индекс текущего шага из step_data
        index = step_data['index_step']

        if 0 <= index < len(current_steps):
            current_step = current_steps[index]

            # Обновляем только те поля шага, которые пришли в step_data (кроме reflection_results)
            for key, value in step_data.items():
                current_step[key] = value

        query = update(RunCase).where(RunCase.run_id == run_id).values(steps=current_steps)
        await session.execute(query)


Base = declarative_base()


class RunCase(Base):
    __tablename__ = "run_cases"

    run_id = Column(UUID(as_uuid=True), primary_key=True)
    case_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=True)
    run_summary = Column(String, nullable=True)
    video = Column(JSON, nullable=True)
    steps = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    start_dt = Column(DateTime(timezone=True))
    end_dt = Column(DateTime(timezone=True))
    complete_time = Column(FLOAT)
    current_case_version = Column(JSON, nullable=True)
    cnt_run = Column(Integer, default=0)


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean(), default=True)
    active_workspace_id = Column(UUID(as_uuid=True), nullable=False)
    extra = Column(JSON, default=dict, nullable=True)
    source = Column(String, nullable=True)
    host = Column(String, nullable=True)
