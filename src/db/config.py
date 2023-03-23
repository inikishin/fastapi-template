from core.config import app_config
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL=f'postgresql+asyncpg://{app_config.db_user}:{app_config.db_pass}@{app_config.db_host}:{app_config.db_port}/{app_config.db_name}'

Base = declarative_base()

engine = create_async_engine(DATABASE_URL,
                             echo=app_config.db_show_queries,
                             future=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
