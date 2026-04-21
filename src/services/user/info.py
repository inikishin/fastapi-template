from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.postgres.db_config import get_session
from src.models.dbo.models import User
from src.models.managers import UserManager
from src.services.common import BaseService


class UserInfoService(BaseService):
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_manager = UserManager(db)

    async def get_user_by_id(self, user_id) -> User | None:
        return await self.user_manager.get_user_by_id(user_id)

    async def get_user_by_tg_chat_id(self, tg_chat_id) -> User | None:
        users = await self.user_manager.get_users_by_filters(tg_chat_id=str(tg_chat_id))
        return users[0] if len(users) > 0 else None


async def get_user_service(
    db: AsyncSession = Depends(get_session),
) -> UserInfoService:
    return UserInfoService(db=db)
