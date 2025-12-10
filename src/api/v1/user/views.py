from fastapi import APIRouter, Depends, HTTPException

from starlette.requests import Request

from src.api.schemes import ResponseGroup
from src.api.v1.user.schemes import UserMeResponse
from src.config.logger import LoggerProvider
from src.services.user.info import get_user_service, UserInfoService
from src.utils.helpers import get_responses, catch_all_exceptions

log = LoggerProvider().get_logger(__name__)

user_router = APIRouter(
    prefix="/user",
    tags=["User"],
)


@user_router.get(
    "/{user_id}",
    description="Get user info",
    responses={
        200: {
            "model": UserMeResponse,
            "description": "User info response",
        },
        **get_responses(ResponseGroup.ALL_ERRORS),
    },
)
@catch_all_exceptions
async def info(
    request: Request,
    user_id: int,
    user_info_service: UserInfoService = Depends(get_user_service),
):
    user = await user_info_service.get_user_by_id(user_id)
    if user:
        return UserMeResponse(
            id=user.id,
            username=user.username,
            email=user.email,
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")
