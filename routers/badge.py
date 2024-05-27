import hashlib
import json
import logging
import os
import time

import redis
from fastapi import APIRouter, Depends, Request

from dependencies import get_token_header

router = APIRouter(
    prefix="/badge",
    tags=["badge"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


def generate_short_hash(uuid, mac_address):
    timestamp = str(time.time())

    # Concatenate the UUID, MAC address, and timestamp
    combined_string = uuid + mac_address + timestamp
    hash_object = hashlib.sha256(combined_string.encode())
    hash_hex = hash_object.hexdigest()

    # Reduce the hash to the first 6 characters
    short_hash = hash_hex[:8]

    return short_hash


def set_registration_keys(uuid, mac):
    logger.info("Creating a registration code by uuid and mac.")
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
    registration_hash = generate_short_hash(uuid, mac)

    hash_in_rd = rd_con.get(registration_hash)
    logger.info(registration_hash)
    logger.info(hash_in_rd)  # returns None if not exists

    # check for hash collisions
    while hash_in_rd is not None:
        hash_in_rd = hash_in_rd.decode("utf-8")
        found_uuid = hash_in_rd.split("|")[0]
        found_mac = hash_in_rd.split("|")[1]

        # they somehow duped the key... so just use the current hash and extend TTL
        if found_uuid == uuid and found_mac == mac:
            break

        time.sleep(1)
        registration_hash = generate_short_hash(uuid, mac)

        hash_in_rd = rd_con.get(registration_hash)
        logger.info(registration_hash)
        logger.info(hash_in_rd)

    rd_con.set(registration_hash, f"{uuid}|{mac}", ex=60 * 15)  # TTL 15min
    rd_con.set(f"{uuid}|{mac}", registration_hash, ex=60 * 15)
    return registration_hash


def get_registration_code(uuid, mac):
    logger.info("Retrieving code by uuid and mac.")
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)

    hash_in_rd = rd_con.get(f"{uuid}|{mac}")
    logger.info(hash_in_rd)

    return hash_in_rd


@router.post("/push-redis")
async def test_redis(request: Request):
    logger.info(os.getenv("REDIS_HOST"))
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
    ret_val = rd_con.set("test", "asdf")

    response = {"status": "SUCCESS", "redis_retval": json.dumps(ret_val)}
    return response


@router.get("/pull-redis")
async def test_redis(request: Request):
    logger.info(os.getenv("REDIS_HOST"))
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
    ret_val = rd_con.get("test")

    response = {"status": "SUCCESS", "redis_retval": json.dumps(ret_val.decode())}
    return response


@router.post("/register")
async def register_badge(request: Request):
    has_registered = 0
    registration_code = None
    if len(request.user) > 0:
        has_registered = 1
    else:
        panda_xpress = request.headers["panda-xpress"]
        panda_mac = request.headers["panda-mac"]

        registration_code = get_registration_code(panda_xpress, panda_mac)
        if not registration_code:
            registration_code = set_registration_keys(panda_xpress, panda_mac)

    response = {"status": "SUCCESS", "registered": json.dumps(has_registered), "registration_code": registration_code}
    return response


@router.post("/verify")
async def verify_badge(request: Request):
    has_registered = 0
    registration_code = None
    if len(request.user) > 0:
        has_registered = 1
        if await request.body():
            req_info = await request.json()
            rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
            pub_body = {"user_uuid": request.headers["panda-xpress"], "mac_address": request.headers["panda-mac"]}

            if req_info.get("hs"):
                pub_body["event"] = "high-score"
                pub_body["high_scores"] = req_info["hs"]
            elif req_info.get("status"):
                pub_body["event"] = "status"
                pub_body["status"] = req_info["status"]

            rd_con.publish("high-score-processor", json.dumps(pub_body))
    else:
        panda_xpress = request.headers["panda-xpress"]
        panda_mac = request.headers["panda-mac"]

        registration_code = get_registration_code(panda_xpress, panda_mac)
        if not registration_code:
            registration_code = set_registration_keys(panda_xpress, panda_mac)

    response = {"status": "SUCCESS", "registered": json.dumps(has_registered), "registration_code": registration_code}
    return response


@router.get("/event/queue")
async def get_event_from_badge_event_queue(request: Request):
    params = {"uuid": request.user[0]["uuid"], "mac_address": request.user[0]["mac_address"]}
    QRY = """
    select id, badge_action, event_message
    from badge_event_queue 
    where recipient_uuid = %(uuid)s and recipient_mac_address = %(mac_address)s
    and has_read = 0
    ORDER BY ID ASC 
    LIMIT 1 
    """
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    event = records.to_dict("records")
    if len(event) > 0:
        event = event[0]
        QRY = "UPDATE badge_event_queue set has_read = 1 where id=%(id)s;"
        params = {"id": event["id"]}
        logger.info(params)
        record_id = request.app.state.db.execute(query=QRY, args=params)
        logger.info(f"Updated badge_event_queue ID {record_id} to has read")
    # response = {
    #     "status": "SUCCESS",
    #     json.dumps(event)
    # }
    return event


# TODO -> REMOVE THIS BEFORE CON DAY
@router.post("/event/queue/reset")
async def admin_reset_badge_queue_events(request: Request):
    QRY = """update badge_event_queue set has_read = 0;"""
    record_id = request.app.state.db.execute(query=QRY)
    response = {"status": "SUCCESS", "data": json.dumps(record_id)}
    return response
