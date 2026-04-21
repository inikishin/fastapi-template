from sqlalchemy import select

from src.config.logger import LoggerProvider
from src.models.dbo.models import User
from src.models.managers.common import BaseManager

log = LoggerProvider().get_logger(__name__)


class UserManager(BaseManager):
    entity = User

    text_search_fields = {
        "username": "ilike",
        "email": "ilike",
    }

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Fetch a user by integer id. Alias of BaseManager.get_by_id for readability."""
        return await self.get_by_id(user_id)

    async def get_users_by_filters(self, **filters) -> list[User]:
        """Example of a custom query; prefer BaseManager.search + apply_filters for new managers."""
        query = select(User)

        for key, value in filters.items():
            if hasattr(User, key):
                query = query.where(getattr(User, key) == value)

        result = await self.db.execute(query)
        users = result.scalars().all()
        return users if users else []
