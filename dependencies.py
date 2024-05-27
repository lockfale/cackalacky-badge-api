import logging
from typing import Optional

from fastapi import Header, HTTPException
from starlette.authentication import AuthenticationBackend, AuthenticationError
from starlette.requests import Request


async def get_token_header(request: Request, panda_xpress: Optional[str] = Header(None), panda_mac: Optional[str] = Header(None)):
    if request.url.path == "/capturetheflag":
        return

    if panda_xpress is None:
        raise HTTPException(status_code=400, detail="X-Token header invalid - panda-xpress missing")

    if panda_mac is None:
        raise HTTPException(status_code=400, detail="X-Token header invalid - panda-mac is missing")


class BearerTokenAuthBackend(AuthenticationBackend):
    async def authenticate(self, request):
        # This function is inherited from the base class and called by some other class
        if "/docs" in request.url.path or "/openapi" in request.url.path:
            pass
        else:
            logging.info(request.url.path)
            if request.url.path == "/config/mac/register":
                return ("asdf", "qwerty"), []
            if request.url.path == "/capturetheflag":
                return ("asdf", "qwerty"), []
            if "panda-xpress" not in request.headers:
                raise HTTPException(status_code=400, detail="X-Token header invalid - panda-xpress missing")

            if "panda-mac" not in request.headers:
                raise HTTPException(status_code=400, detail="X-Token header invalid - panda-mac is missing")

            panda_xpress = request.headers["panda-xpress"]
            panda_mac = request.headers["panda-mac"]
            if panda_xpress is None:
                raise HTTPException(status_code=400, detail="X-Token header invalid - panda-xpress empty")

            if panda_mac is None:
                raise HTTPException(status_code=400, detail="X-Token header invalid - panda-mac is empty")

            params = {"uuid": panda_xpress, "mac_address": panda_mac}
            user = request.app.state.db.select_dataframe(
                query="select * from users where uuid = %(uuid)s and mac_address = %(mac_address)s", args=params
            )

            if len(user) == 0:
                if request.url.path == "/badge/verify" or request.url.path == "/badge/register":
                    return (panda_xpress, panda_mac), []
                raise HTTPException(status_code=401, detail="Invalid panda-xpress & panda-mac combination.")

            return (panda_xpress, panda_mac), user.to_dict("records")
