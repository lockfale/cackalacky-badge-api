import json
import logging
import os

import redis
from fastapi import APIRouter, Depends, HTTPException, Request

from dependencies import get_token_header

router = APIRouter(
    prefix="/games",
    tags=["games"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


def add_limit_and_offset(query: str):
    return f"""{query} LIMIT %(limit)s 
    OFFSET %(offset)s"""


def simple_sort(query: str, query_category: str, sort_by: str, table_alias: str):
    """
    best
    worst
    recent
    stale

    :param sort_by:
    :return:
    """
    mapper = {
        "game": {
            "asc": {"field": "game_name", "order": "asc"},
            "desc": {"field": "game_name", "order": "desc"},
            "default": {"field": "game_name", "order": "asc"},
        },
        "score": {
            "best": [{"field": "score", "order": "desc"}, {"field": "duration", "order": "asc"}],
            "worst": [{"field": "score", "order": "asc"}, {"field": "duration", "order": "desc"}],
            "recent": {"field": "id", "order": "desc"},
            "stale": {"field": "id", "order": "asc"},
            "default": [{"field": "score", "order": "desc"}, {"field": "duration", "order": "asc"}],
        },
    }
    # Get the field and order for sorting
    sort_fields = mapper.get(query_category, {}).get(sort_by, "default")
    if not isinstance(sort_fields, list):
        sort_fields = [sort_fields]

    # Build the ORDER BY clause
    order_by_fields = ", ".join([f"{table_alias}.{f['field']} {f['order']}" for f in sort_fields])
    order_by = f"ORDER BY {order_by_fields}"
    # Add the ORDER BY clause to the query
    sorted_query = f"{query} {order_by}"
    return sorted_query


def check_page_and_offset_values(page: int, pageSize: int):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be a positive integers greater than or equal to 1")

    if pageSize < 1:
        raise HTTPException(status_code=400, detail="Page size must be a positive integer greater than 0")


@router.get("/list")
async def get_game_list(request: Request, page: int = 1, pageSize: int = 10, sortBy: str = "asc"):
    check_page_and_offset_values(page, pageSize)
    params = {"limit": pageSize, "offset": (page - 1) * pageSize}
    QRY = """
        select gl.game_name from game_list gl
    """
    QRY = simple_sort(QRY, "game", sortBy, "gl")
    QRY = add_limit_and_offset(QRY)
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.get("/leaderboard/{game}")
async def get_game_leaderboard(game: str, request: Request, page: int = 1, pageSize: int = 10, sortBy: str = "best"):
    check_page_and_offset_values(page, pageSize)
    params = {"game": game, "limit": pageSize, "offset": (page - 1) * pageSize}
    QRY = """
        SELECT gs.game_name, gs.score, gs.duration, coalesce(usrs.discord_handle, NULL) as discord_handle
        FROM cackalacky.game_score gs
        JOIN users usrs on usrs.uuid = gs.user_uuid
        where gs.game_name = %(game)s
    """
    QRY = simple_sort(QRY, "score", sortBy, "gs")
    QRY = add_limit_and_offset(QRY)
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.get("/me")
async def get_my_games(request: Request, page: int = 1, pageSize: int = 10, sortBy: str = "best"):
    check_page_and_offset_values(page, pageSize)
    params = {"uuid": request.user[0]["uuid"], "limit": pageSize, "offset": (page - 1) * pageSize}
    QRY = """
        SELECT gs.game_name, gs.score, gs.duration, coalesce(usrs.discord_handle, NULL) as discord_handle
        FROM cackalacky.game_score gs
        JOIN users usrs on usrs.uuid = gs.user_uuid
        where user_uuid = %(uuid)s
        """
    QRY = simple_sort(QRY, "score", sortBy, "gs")
    QRY = add_limit_and_offset(QRY)
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.get("/me/{game}")
async def get_my_game_score(request: Request, game: str, page: int = 1, pageSize: int = 10, sortBy: str = "best"):
    check_page_and_offset_values(page, pageSize)
    params = {"uuid": request.user[0]["uuid"], "game": game, "limit": pageSize, "offset": (page - 1) * pageSize}
    QRY = """
    SELECT gs.game_name, gs.score, gs.duration, coalesce(usrs.discord_handle, NULL) as discord_handle
        FROM cackalacky.game_score gs
        JOIN users usrs on usrs.uuid = gs.user_uuid
    where user_uuid = %(uuid)s AND game_name = %(game)s
    """
    QRY = simple_sort(QRY, "score", sortBy, "gs")
    QRY = add_limit_and_offset(QRY)
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.post("/me/{game}")
async def insert_my_game_score(request: Request, game: str):
    GET_GAME_ID_QRY = """
        select gl.id from game_list gl where game_name = %(game)s
    """

    QRY = "INSERT INTO game_score (game_id, game_name, score, duration, user_uuid, user_mac_address) VALUES (%(game_id)s, %(game)s, %(score)s, %(duration)s, %(uuid)s, %(mac_address)s) RETURNING id;"
    if await request.body():
        req_info = await request.json()

        game_id = request.app.state.db.select_dataframe(query=GET_GAME_ID_QRY, args={"game": game})
        if len(game_id) == 0:
            return {"status": "ERROR", "data": {"message": f"Game: {game} not found"}}

        params = {
            "game_id": game_id.to_dict("records")[0]["id"],
            "uuid": request.user[0]["uuid"],
            "mac_address": request.user[0]["mac_address"],
            "game": game,
            "score": req_info["score"],
            "duration": req_info["duration"],
        }
        logger.info(params)
        record_id = request.app.state.db.execute(query=QRY, args=params)
        response = {"status": "SUCCESS", "data": {"record_id": record_id}}
        logger.info(response)
        rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
        rd_con.publish(
            "high-score-processor",
            json.dumps({"event": "around-the-world", "user_uuid": request.headers["panda-xpress"], "mac_address": request.headers["panda-mac"]}),
        )
        rd_con.publish(
            "high-score-processor",
            json.dumps(
                {
                    "event": "challenge-check",
                    "user_uuid": request.headers["panda-xpress"],
                    "mac_address": request.headers["panda-mac"],
                    "score_id": record_id,
                }
            ),
        )
    else:
        response = {"status": "SUCCESS", "data": "No body passed. Nothing written"}
    return response
