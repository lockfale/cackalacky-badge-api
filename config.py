import os
from pathlib import Path

from pydantic import BaseSettings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


class SettingsFromEnvironment(BaseSettings):
    """Defines environment variables with their types and optional defaults"""

    db_host: str = os.getenv("PG_DB_HOST")
    db_user: str = os.getenv("PG_DB_USER")
    db_password: str = os.getenv("PG_DB_PASSWORD")
    db_port: str = os.getenv("PG_DB_PORT")
    db_database: str = os.getenv("PG_DB_DATABASE")
    db_connection_limit: str = os.getenv("PG_DB_CONNECTION_LIMIT")
