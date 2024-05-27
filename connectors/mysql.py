import logging
from typing import Any, Dict

import pandas as pd
from mysql.connector import Error, pooling

import config


class MySQLConnectionError(Exception):
    pass


class MySQLConnector:
    __mysqlconn = None

    def __init__(self):
        self._retries = 3

    def connect(self, settings: config.SettingsFromEnvironment):
        if self.__mysqlconn is None:
            try:
                self.__mysqlconn = pooling.MySQLConnectionPool(pool_name="cackapool",
                                                              pool_size=int(settings.db_connection_limit),
                                                              pool_reset_session=True,
                                                              host=settings.db_host,
                                                              database=settings.db_database,
                                                              user=settings.db_user,
                                                              port=settings.db_port,
                                                              password=settings.db_password)
                logging.info(f"Connection Pool Name - {self.__mysqlconn.pool_name}")
                logging.info(f"Connection Pool Size - {self.__mysqlconn.pool_size}")

            except Exception as e:
                logging.error(e)
                raise MySQLConnectionError(e)

    def release_resources(self, connection_object=None, cursor=None):
        try:
            if cursor:
                cursor.close()

            if connection_object and connection_object.is_connected():
                connection_object.close()
                logging.info("MySQL connection is closed")
        except Exception as e:
            logging.error("Issue closing cursor or connection")
            logging.error(e)

    def execute(self, query: str, args: Dict[str, Any] = None):
        available_calls = self._retries
        connection_object = None
        cursor = None

        while available_calls >= 0:
            try:
                # Get connection object from a pool
                connection_object = self.__mysqlconn.get_connection()
                ret_val = None

                if connection_object.is_connected():
                    cursor = connection_object.cursor()
                    cursor.execute(query, args)
                    connection_object.commit()
                    if "insert into" in query.lower():
                        ret_val = cursor.lastrowid

                    self.release_resources(connection_object, cursor)
                    return ret_val

            except Error as e:
                logging.error("Error while connecting to MySQL using Connection pool ", e)
                self.release_resources(connection_object, cursor)
                available_calls -= 1

    def select_dataframe(self, query: str, args: Dict[str, Any] = None) -> pd.DataFrame:
        available_calls = self._retries
        connection_object = None

        while available_calls >= 0:
            try:
                # Get connection object from a pool
                connection_object = self.__mysqlconn.get_connection()

                if connection_object.is_connected():
                    data = pd.read_sql_query(sql=query, con=connection_object, params=args)
                    self.release_resources(connection_object)
                    return data

            except Error as e:
                logging.error("Error while connecting to MySQL using Connection pool ", e)
                self.release_resources(connection_object)
                available_calls -= 1
