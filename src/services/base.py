from abc import ABC, abstractmethod

from fastapi import Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.config import get_session
from db.models.entity import Entity as EntityDbModel
from models.base import Entity


class BaseEntityService(ABC):
    @abstractmethod
    async def get_entities(self) -> list[Entity]:
        pass


class EntityPostgresService(BaseEntityService):
    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    async def get_entities(self) -> list[Entity]:
        query = select(EntityDbModel)
        result = await self.session.execute(query)
        result = result.scalars()
        print(result)
        return [Entity(title=item.title) for item in result]


def get_entity_service(
    session: AsyncSession = Depends(get_session),
) -> BaseEntityService:
    return EntityPostgresService(session)
