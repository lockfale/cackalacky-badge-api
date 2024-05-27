import logging
import os
import random
import socket
import string
import time
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware

import config
from catch_http_exceptions import catch_http_exceptions
from connectors.pgsql import PostgreSQLConnector
from dependencies import BearerTokenAuthBackend
from metrics_middleware import MetricsMiddleware
from routers import (
    alcohol,
    badge,
    badge_registration,
    capturetheflag,
    games,
    otel_test,
    secret_flag,
    tests,
)
from s3_logger import S3TimedRotatingFileHandler

logger = logging.getLogger("s3logger")
logger.setLevel(logging.INFO)
hostname = socket.gethostname()
s3_handler = S3TimedRotatingFileHandler(
    f"{hostname}.log",
    bucket_name=os.getenv("BUCKET_NAME"),
    aws_access_key_id=os.getenv("AWS_LOGGER_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_LOGGER_SECRET_KEY"),
    when="M",
    interval=1,
    backupCount=5,
)
formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s")
s3_handler.setFormatter(formatter)
logger.addHandler(s3_handler)

app = FastAPI()
app.include_router(alcohol.router)
app.include_router(games.router)
app.include_router(tests.router)
app.include_router(badge.router)
app.include_router(capturetheflag.router)
app.include_router(secret_flag.router)
app.include_router(otel_test.router)
app.include_router(badge_registration.router)


@lru_cache()
def get_settings():
    return config.SettingsFromEnvironment()


origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://badge.cackalacky.ninja",
    "https://badge.cackalacky.ninja",
    "badge.cackalacky.ninja",
]

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(AuthenticationMiddleware, backend=BearerTokenAuthBackend())
app.middleware("http")(catch_http_exceptions)

skip_metrics = os.getenv("SKIP_METRICS", "False").lower() in ["true", "1", "t"]
logger.info(f"Skip metrics? {skip_metrics}")
if not skip_metrics:
    app.add_middleware(MetricsMiddleware)

# Get the host name of the machine
host_name = socket.gethostname()
logger.info(f"Host name: {host_name}")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    idem = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    # Log request path, headers, and query parameters
    panda_xpress = dict(request.headers).get("panda-xpress")
    panda_mac = dict(request.headers).get("panda-mac")
    query_params = dict(request.query_params)
    logger.info(
        f"rid={idem} start request remote-ip={request.client.host} path={request.url.path} panda_xpress={panda_xpress} panda_mac={panda_mac} query_params={query_params}"
    )

    start_time = time.time()
    response = await call_next(request)
    content_length = response.headers["content-length"]
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = "{0:.2f}".format(process_time)
    logger.info(f"rid={idem} content_length={content_length} completed_in={formatted_process_time}ms status_code={response.status_code}")

    return response


@app.on_event("startup")
async def startup_event():
    pgsql_db = PostgreSQLConnector()
    pgsql_db.connect(get_settings())
    app.state.db = pgsql_db
    logger.info(f"Starting badge api.py - {os.getenv('APP_NAME')} | {os.getenv('APP_ENV')}")


@app.on_event("shutdown")
async def shutdown_event():
    if not app.state.db:
        await app.state.db.close()
    logger.info("Server Shutdown")
