import json
import logging
import os
import re
from typing import Optional

import redis
import requests

from connectors.pgsql import PostgreSQLConnector
from utilities.achievements import (
    Achievement,
    StaffMember,
    get_achievement_by_ctf_id_and_user_id,
    get_random_staff_member,
    insert_user_achievement,
)
from utilities.events import log_event
from utilities.users import User, get_user_by_device


class UserNotRegisteredException(Exception):
    pass


logger = logging.getLogger("s3logger")


def get_registration_code(uuid, mac):
    logger.info("Retrieving code by uuid and mac.")
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)

    hash_in_rd = rd_con.get(f"{uuid}|{mac}")
    logger.info(hash_in_rd)

    return hash_in_rd


def replace_string_in_text(text, search_string, replacement_string):
    regex = re.compile(re.escape(search_string), re.IGNORECASE)
    return re.sub(regex, replacement_string, text)


def get_fact():
    url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
    response = requests.get(url)
    try:
        return response.json()
    except Exception as e:
        logger.error(e)


def send_fact_to(db_connection: PostgreSQLConnector):
    staff_member: StaffMember = get_random_staff_member(db_connection)
    fact_dict = get_fact()
    logger.info(fact_dict)
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)

    last_sent_fact = rd_con.get("last_sent_fact")
    if last_sent_fact is None:
        rd_con.set("last_sent_fact", fact_dict.get("text", "OOPS"), ex=60)  # TTL 1min
        rd_con.publish(
            "fact",
            json.dumps(
                {
                    "fact": fact_dict.get("text", "OOPS"),
                    "discord_handle": staff_member.discord_handle,
                    "discord_user_id": staff_member.discord_user_id,
                }
            ),
        )


def ctf_action(db_connection: PostgreSQLConnector, uuid: str, mac_address: str, event_id: int, achievement: Achievement):
    message = f'Someone unlocked achievement: "{achievement.name}" but we don\'t know who... they should register their badge!'
    status = "SUCCESS"

    if uuid is not None and mac_address is not None:
        r = log_event(db_connection, event_id, uuid, mac_address)
        logger.info(f"Event logged {r}")
        try:
            user_record: Optional[User] = get_user_by_device(db_connection, uuid, mac_address)
            if not user_record:
                raise UserNotRegisteredException(f"User with badge: {uuid} | {mac_address} does not exist. They probably haven't registered yet.")

            achievement_info = get_achievement_by_ctf_id_and_user_id(db_connection, user_record.id, achievement.id)
            logger.info(achievement_info)
            rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
            if achievement_info.user_has_achievement == 1:
                achievement_name = achievement.name
                if achievement_name == "Badge Access Point":
                    achievement_name = "[REDACTED]"

                message = f"{user_record.discord_handle} has already unlocked: {achievement_name}"
                rd_con.publish("community-message", message)
            else:
                message = f"{user_record.discord_handle} unlocked: {achievement.name} for {achievement.points} points!"
                insert_user_achievement(db_connection, user_record.id, achievement.id)
                rd_con.publish(
                    "achievement",
                    json.dumps(
                        {
                            "handle": user_record.discord_handle,
                            "name": achievement.name,
                            "description": achievement.description,
                            "points": achievement.points,
                        }
                    ),
                )
            send_fact_to(db_connection)
        except UserNotRegisteredException as e:
            logger.error(f"{e.__class__.__name__} caught: {e}")
            status = "ERROR"
            message = f"User device is not registered: {e}"
        except Exception as e:
            logger.error(f"An unknown error occurred: {e}")
            status = "ERROR"
            message = f"Some unknown bullshit happened: {e}"

    return {"status": status, "message": message}
