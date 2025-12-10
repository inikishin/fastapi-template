from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import LoggerProvider

from src.models.dbo.models import User

log = LoggerProvider().get_logger(__name__)


class UserManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get_users_by_filters(self, **filters) -> list[User]:
        query = select(User)

        for key, value in filters.items():
            if hasattr(User, key):
                query = query.where(getattr(User, key) == value)

        result = await self.db.execute(query)
        users = result.scalars().all()
        return users if users else []
