import logging
from typing import Optional

from fastapi import APIRouter, Depends

from models.base import EchoParamsResponse, EchoRequest, EchoResponse, Entity
from services.base import BaseEntityService, get_entity_service

logger = logging.getLogger(__name__)
TAG = ["template"]
router = APIRouter()


@router.get("/", tags=TAG, description="Get API version")
async def root_handler():
    return {"version": "v1"}


@router.get("/echo/{name}", tags=TAG, description="Echo GET method")
async def get_echo(name: str, age: int, sex: Optional[str] = None) -> EchoResponse:
    return EchoResponse(name=name, params=EchoParamsResponse(age=age, sex=sex))


@router.post("/echo/{param}", tags=TAG, description="Echo POST method")
async def post_echo(param: str, item: EchoRequest) -> EchoRequest:
    logger.info(param)
    return item


@router.get("/entities", tags=TAG)
async def read_entities(
    genre_service: BaseEntityService = Depends(get_entity_service),
) -> list[Entity]:
    entities = await genre_service.get_entities()
    return entities
