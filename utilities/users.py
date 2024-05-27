import logging
from dataclasses import dataclass

from connectors.pgsql import PostgreSQLConnector

logger = logging.getLogger("s3logger")


@dataclass
class User:
    id: int
    first_name: str
    last_name: str
    discord_handle: str
    discord_user_id: str
    uuid: str
    mac_address: str


def get_user_by_device(db_connection: PostgreSQLConnector, uuid, mac_address):
    query = """
    SELECT id, first_name, last_name, discord_handle, discord_user_id, uuid, mac_address
    FROM cackalacky.users
    WHERE uuid = %(uuid)s AND mac_address = %(mac_address)s;
    """

    params = {"uuid": uuid, "mac_address": mac_address}

    try:
        user_df = db_connection.select_dataframe(query, params)
        if len(user_df) == 0:
            return None

        user_dict = user_df.to_dict("records")[0]
        return User(
            id=user_dict["id"],
            first_name=user_dict["first_name"],
            last_name=user_dict["last_name"],
            discord_handle=user_dict["discord_handle"],
            discord_user_id=user_dict["discord_user_id"],
            uuid=user_dict["uuid"],
            mac_address=user_dict["mac_address"],
        )
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
