import logging

from fastapi import APIRouter, Depends, Request

from dependencies import get_token_header
from routers.capturetheflag import ctf_action
from utilities.achievements import Achievements

router = APIRouter(
    prefix="/secret",
    tags=["secret"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


@router.get("/flag")
async def ctf_secret_flag(request: Request):
    eventId = 17
    achievements = Achievements()
    response = ctf_action(request.app.state.db, request.user[0]["uuid"], request.user[0]["mac_address"], eventId, achievements.SECRET_FLAG)
    logger.info(response)
    return response
