import asyncio
import logging

from fastapi import APIRouter, Depends

from dependencies import get_token_header

router = APIRouter(
    tags=["otel-test"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


@router.get("/api/fast")
async def fast_endpoint():
    return "fast ok"


@router.get("/api/slow")
async def slow_endpoint():
    await asyncio.sleep(2)
    return "slow ok"
