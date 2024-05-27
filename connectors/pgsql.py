import logging
from typing import Any, Dict

import pandas as pd
from psycopg2 import DatabaseError, pool

import config

logger = logging.getLogger('s3logger')


class PostgreSQLConnectionError(Exception):
    pass


class DuplicateKeyException(Exception):
    pass


def nullify(value):
    return value if value is not None else None

class PostgreSQLConnector:
    __pgconn = None

    def __init__(self):
        self._retries = 3

    def connect(self, settings: config.SettingsFromEnvironment):
        if self.__pgconn is None:
            try:
                self.__pgconn = pool.SimpleConnectionPool(1, int(settings.db_connection_limit),
                                                          host=settings.db_host,
                                                          database=settings.db_database,
                                                          user=settings.db_user,
                                                          port=settings.db_port,
                                                          password=settings.db_password)
                logger.info(f"Connection Pool Size - {self.__pgconn.minconn}-{self.__pgconn.maxconn}")

            except Exception as e:
                logger.error(e)
                raise PostgreSQLConnectionError(e)

    def release_resources(self, connection_object=None, cursor=None):
        try:
            if cursor:
                cursor.close()

            if connection_object:
                self.__pgconn.putconn(connection_object)
                logger.info("PostgreSQL connection is closed")

        except Exception as e:
            logger.error("Issue closing cursor or connection")
            logger.error(e)

    def execute(self, query: str, args: Dict[str, Any] = None):
        available_calls = self._retries
        connection_object = None
        cursor = None

        logger.info(query)
        logger.info(args)

        while available_calls >= 0:
            ret_val = None
            try:
                # Get connection object from a pool
                connection_object = self.__pgconn.getconn()
                cursor = connection_object.cursor()
            except DatabaseError as e:
                logger.error("Error while connecting to PostgreSQL using Connection pool", e)
                self.release_resources(connection_object, cursor)
                available_calls -= 1

            try:
                cursor.execute(query, args)
                connection_object.commit()

                if "insert into" in query.lower():
                    logger.info(cursor)
                    ret_val = cursor.fetchone()[0]

                self.release_resources(connection_object, cursor)
                return ret_val
            except Exception as e:
                self.release_resources(connection_object, cursor)
                logger.error(e)
                available_calls -= 1

    def select_dataframe(self, query: str, args: Dict[str, Any] = None) -> pd.DataFrame:
        available_calls = self._retries
        connection_object = None

        logger.info(query)
        logger.info(args)

        while available_calls >= 0:
            try:
                # Get connection object from a pool
                connection_object = self.__pgconn.getconn()

                data = pd.read_sql_query(sql=query, con=connection_object, params=args)
                self.release_resources(connection_object)
                return data

            except DatabaseError as e:
                logger.error("Error while connecting to PostgreSQL using Connection pool", e)
                self.release_resources(connection_object)
                available_calls -= 1
