import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

connect_args = {}
db_url = settings.database_url

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "asyncpg" in db_url:
    # Use psycopg async driver with proper SSL for Render PostgreSQL
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    # Strip any query params
    if "?" in db_url:
        db_url = db_url.split("?")[0]
    # Create permissive SSL context (Render uses self-signed certs)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connect_args = {"sslmode": "require", "ssl_context": ssl_ctx}

engine = create_async_engine(db_url, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Add columns that create_all won't add to existing tables
    async with engine.begin() as conn:
        for col, coltype in [
            ("label_file_data", "BYTEA"),
            ("label_file_mime", "VARCHAR(50)"),
            ("name", "VARCHAR(255)"),
        ]:
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE verification_reports ADD COLUMN IF NOT EXISTS {col} {coltype}"
                    )
                )
            except Exception:
                pass
