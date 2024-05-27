import datetime
import json
import logging

import pandas as pd
from fastapi import APIRouter, Depends, Request

from dependencies import get_token_header

router = APIRouter(
    tags=["tests"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


@router.post("/test")
async def test(info: Request):
    if await info.body():
        req_info = await info.json()
        logger.info(req_info)
        response = {"status": "SUCCESS", "data": {"sample": f"you sent: {req_info}"}}
    else:
        response = {"status": "SUCCESS"}
    logger.info(response)
    return response


@router.get("/ping")
def ping():
    response = {"status": "SUCCESS", "data": "pong"}
    logger.info(response)
    return response


@router.get("/time")
def get_time():
    response = {"status": "SUCCESS", "data": datetime.datetime.now()}
    logger.info(response)
    return response


@router.get("/db-get")
def db_test_get(request: Request):
    records = request.app.state.db.select_dataframe(query="select * from test_table")
    # unsure as to why this isn't fussy but the get by ID is... dumbass timestamps
    records["created_at"] = records["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    records["updated_at"] = records["updated_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.get("/db-get/{item_id}")
def db_test_get_by_id(item_id: int, request: Request):
    params = {"id": item_id}
    records = request.app.state.db.select_dataframe(query="select * from test_table where id = %(id)s", args=params)
    # this seems really unnecessary and I hate it... will probably not select timestamps
    records["created_at"] = pd.to_datetime(records.created_at, format="%Y-%m-%d %H:%M:%S")
    records["created_at"] = records["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    records["updated_at"] = pd.to_datetime(records.updated_at, format="%Y-%m-%d %H:%M:%S")
    records["updated_at"] = records["updated_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    response = {"status": "SUCCESS", "data": json.dumps(records.to_dict("records"))}
    logger.info(response)
    return response


@router.post("/db-insert")
async def db_test_post(request: Request):
    QRY = "INSERT INTO `test_table` (`test_varchar_col`, `test_int_col`) VALUES (%(test_vc)s, %(test_int)s);"
    if await request.body():
        req_info = await request.json()
        params = {"test_vc": req_info["test_vc"], "test_int": req_info["test_int"]}
        logger.info(params)
        record_id = request.app.state.db.execute(query=QRY, args=params)
        response = {"status": "SUCCESS", "data": {"record_id": record_id}}
        logger.info(response)
    else:
        response = {"status": "SUCCESS", "data": "No body passed. Nothing written"}
    return response


@router.post("/db-insert")
async def db_test_post(request: Request):
    QRY = "INSERT INTO `test_table` (`test_varchar_col`, `test_int_col`) VALUES (%(test_vc)s, %(test_int)s);"
    if await request.body():
        req_info = await request.json()
        params = {"test_vc": req_info["test_vc"], "test_int": req_info["test_int"]}
        logger.info(params)
        record_id = request.app.state.db.execute(query=QRY, args=params)
        response = {"status": "SUCCESS", "data": {"record_id": record_id}}
        logger.info(response)
    else:
        response = {"status": "SUCCESS", "data": "No body passed. Nothing written"}
    return response
