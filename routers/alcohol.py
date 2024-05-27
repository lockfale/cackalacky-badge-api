import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from dependencies import get_token_header

logger = logging.getLogger("s3logger")

router = APIRouter(
    prefix="/alcohol",
    tags=["alcohol"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


def add_limit_and_offset(query: str):
    return f"""{query} LIMIT %(limit)s 
    OFFSET %(offset)s"""


def simple_sort(query: str, sort_by: str, table_alias: str):
    """
    best
    worst
    recent
    stale

    :param sort_by:
    :return:
    """
    mapper = {
        "best": {"field": "reading", "order": "desc"},
        "worst": {"field": "reading", "order": "asc"},
        "recent": {"field": "id", "order": "desc"},
        "stale": {"field": "id", "order": "asc"},
        "default": {"field": "id", "order": "desc"},
    }
    to_sort = mapper.get(sort_by, "default")
    return f"{query} order by {table_alias}.{to_sort['field']} {to_sort['order']}"


def check_page_and_offset_values(page: int, pageSize: int):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be a positive integers greater than or equal to 1")

    if pageSize < 1:
        raise HTTPException(status_code=400, detail="Page size must be a positive integer greater than 0")


@router.get("/list")
async def get_alcohol_list(request: Request, page: int = 1, pageSize: int = 10, sortBy: str = "best"):
    check_page_and_offset_values(page, pageSize)
    params = {"limit": pageSize, "offset": (page - 1) * pageSize}
    QRY = """
        SELECT coalesce(usrs.discord_handle, NULL) as discord_handle, ar.reading 
        FROM alcohol_reading ar 
        join users usrs on usrs.uuid = ar.user_uuid 
    """
    QRY = simple_sort(QRY, sortBy, "ar")
    QRY = add_limit_and_offset(QRY)
    logger.info(QRY)
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.get("/leaderboard")
async def get_alcohol_leaderboard(request: Request, page: int = 1, pageSize: int = 10, sortBy: str = "best"):
    check_page_and_offset_values(page, pageSize)
    params = {"limit": pageSize, "offset": (page - 1) * pageSize}
    QRY = """
            SELECT coalesce(usrs.discord_handle, NULL) as discord_handle, ar.reading 
            FROM alcohol_reading ar 
            join users usrs on usrs.uuid = ar.user_uuid 
        """
    QRY = simple_sort(QRY, sortBy, "ar")
    QRY = add_limit_and_offset(QRY)
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.get("/me")
async def get_my_alcohol_readings(request: Request, page: int = 1, pageSize: int = 10, sortBy: str = "best"):
    check_page_and_offset_values(page, pageSize)
    params = {"uuid": request.user[0]["uuid"], "limit": pageSize, "offset": (page - 1) * pageSize}
    QRY = """
            SELECT coalesce(usrs.discord_handle, NULL) as discord_handle, ar.reading 
            FROM alcohol_reading ar 
            join users usrs on usrs.uuid = ar.user_uuid 
        """
    QRY = simple_sort(QRY, sortBy, "ar")
    QRY = add_limit_and_offset(QRY)
    records = request.app.state.db.select_dataframe(query=QRY, args=params)
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.post("/me")
async def insert_alcohol_reading(request: Request):
    QRY = "INSERT INTO alcohol_reading (user_uuid, reading) VALUES (%(uuid)s, %(reading)s) RETURNING id;"
    if await request.body():
        req_info = await request.json()
        params = {"uuid": request.user[0]["uuid"], "reading": req_info["reading"]}
        logger.info(params)
        record_id = request.app.state.db.execute(query=QRY, args=params)
        response = {"status": "SUCCESS", "data": {"record_id": record_id}}
        logger.info(response)
    else:
        response = {"status": "SUCCESS", "data": "No body passed. Nothing written"}
    return response
