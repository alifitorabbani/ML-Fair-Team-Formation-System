from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config.settings import settings
from app.models.models import Base
import os
from urllib.parse import urlparse, urlunparse

SQLALCHEMY_DATABASE_URL = settings.database_url

# Ensure asyncpg is used for PostgreSQL URLs even if DATABASE_URL omits the driver
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# For PostgreSQL on Vercel, strip all query params to avoid asyncpg receiving unsupported kwargs
# like sslmode/channel_binding from SQLAlchemy's URL translation.
if "postgresql+asyncpg://" in SQLALCHEMY_DATABASE_URL:
    parsed = urlparse(SQLALCHEMY_DATABASE_URL)
    SQLALCHEMY_DATABASE_URL = urlunparse(parsed._replace(query=""))

connect_args: dict = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# On Vercel, enable SSL for asyncpg explicitly if using PostgreSQL
if os.getenv("VERCEL") == "1" and SQLALCHEMY_DATABASE_URL.startswith("postgresql+asyncpg://"):
    connect_args["ssl"] = True
    connect_args["timeout"] = 10

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    poolclass=NullPool if os.getenv("VERCEL") == "1" else None,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
