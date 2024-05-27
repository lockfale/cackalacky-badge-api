import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from dependencies import get_token_header

router = APIRouter(
    tags=["badge", "registration"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


@router.post("/config/mac/register")
async def config_badge_register(request: Request):
    QRY = "INSERT INTO badge_registration (mac_address, chip_id) VALUES (%(mac)s, %(chip_id)s) RETURNING id;"
    if await request.body():
        req_info = await request.json()
        params = {"mac": req_info.get("mac_address", None), "chip_id": req_info.get("chip_id", None)}
        logger.info(params)
        if not params["mac"]:
            raise HTTPException(status_code=400, detail="mac_address is missing")

        if not params["chip_id"]:
            raise HTTPException(status_code=400, detail="chip_id is missing")

        record_id = request.app.state.db.execute(query=QRY, args=params)
        response = {"status": "SUCCESS", "data": {"record_id": record_id}}
        logger.info(response)
    else:
        response = {"status": "SUCCESS", "data": "No body passed. Nothing written"}
    return response
