import json
import logging
import os

import redis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from dependencies import get_token_header
from utilities.achievements import (
    Achievements,
    get_achievement_by_ctf_id_and_user_id,
    insert_user_achievement,
)
from utilities.encrypt_decrypt import decoder
from utilities.events import log_event
from utilities.process_ctf_action import ctf_action
from utilities.users import get_user_by_device


class UserNotRegisteredException(Exception):
    pass


router = APIRouter(
    prefix="/capturetheflag",
    tags=["capturetheflag"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


@router.get("")
def capture_the_flag(request: Request, code: str = None):
    achievements = Achievements()
    decoded_value = decoder(code)

    parts = decoded_value.split("&")
    uuid = parts[0]
    mac_address = parts[1]
    event_id = 17

    if uuid and mac_address:
        log_event(request.app.state.db, event_id, uuid, mac_address)
        user_record = get_user_by_device(request.app.state.db, uuid, mac_address)
        try:
            if not user_record:
                raise UserNotRegisteredException(f"User with badge: {uuid} | {mac_address} does not exist. They probably haven't registered yet.")

            message = f"{user_record.discord_handle} just got Rick Rolled. #pwnd."
            achievement_info = get_achievement_by_ctf_id_and_user_id(request.app.state.db, user_record.id, achievements.RICK_ROLLED.id)
            logger.info(achievement_info)
            rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
            if achievement_info.user_has_achievement == 0:
                insert_user_achievement(request.app.state.db, user_record.id, achievements.RICK_ROLLED.id)
                rd_con.publish(
                    "achievement",
                    json.dumps(
                        {
                            "handle": user_record.discord_handle,
                            "name": achievements.RICK_ROLLED.name,
                            "description": achievements.RICK_ROLLED.description,
                            "points": achievements.RICK_ROLLED.points,
                        }
                    ),
                )
            else:
                message = f"{user_record.discord_handle} was already #pwnd. Guess they wanted more."
                logger.info(message)
                rd_con.publish("community-message", message)
        except UserNotRegisteredException as e:
            logger.error(f"{type(e).__name__} caught: {str(e)}")
            rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
            rd_con.publish("community-message", "Someone got an achievement but didn't register their badge...")
        except Exception as e:
            logger.error(str(e))
    else:
        message = "Someone just got Rick Rolled. #pwnd."
        rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
        rd_con.publish("community-message", message)
        # bot_runner.community_message(message)

    return RedirectResponse("https://rb.gy/8dpuen", status_code=302)


@router.get("/HelloWorld")
async def ctf_hello_world(request: Request):
    eventId = 17
    achievements = Achievements()
    response = ctf_action(request.app.state.db, request.user[0]["uuid"], request.user[0]["mac_address"], eventId, achievements.HELLO_WORLD)

    logger.info(response)
    return response


@router.get("/Serial")
async def ctf_serial(request: Request):
    eventId = 17
    achievements = Achievements()
    response = ctf_action(
        request.app.state.db, request.user[0]["uuid"], request.user[0]["mac_address"], eventId, achievements.SERIAL_PORT_INTERACTION
    )

    logger.info(response)
    return response


@router.get("/APConn")
async def ctf_serial(request: Request):
    eventId = 17
    achievements = Achievements()
    response = ctf_action(request.app.state.db, request.user[0]["uuid"], request.user[0]["mac_address"], eventId, achievements.BADGE_ACCESS_POINT)

    logger.info(response)
    return response


@router.get("/WebAuth")
async def ctf_serial(request: Request):
    eventId = 17
    achievements = Achievements()
    response = ctf_action(request.app.state.db, request.user[0]["uuid"], request.user[0]["mac_address"], eventId, achievements.BADGE_WEB_AUTH)

    logger.info(response)
    return response


@router.get("/FlagTxt")
async def ctf_serial(request: Request):
    eventId = 17
    achievements = Achievements()
    response = ctf_action(request.app.state.db, request.user[0]["uuid"], request.user[0]["mac_address"], eventId, achievements.FLAG_TEXT)
    logger.info(response)
    return response
