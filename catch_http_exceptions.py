from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


async def catch_http_exceptions(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except HTTPException as ex:
        return JSONResponse(content={"detail": ex.detail}, status_code=ex.status_code)
