import logging

from connectors.pgsql import PostgreSQLConnector, nullify

logger = logging.getLogger("s3logger")


def log_event(db_connection: PostgreSQLConnector, event_id, uuid, mac_address):
    insert_columns = ["event_id", "uuid", "mac_address"]
    query = f"INSERT INTO cackalacky.events ({','.join(insert_columns)}) VALUES (%(event_id)s, %(uuid)s, %(mac_address)s) RETURNING id;"

    params = {"event_id": nullify(event_id), "uuid": nullify(uuid), "mac_address": nullify(mac_address)}

    try:
        new_event_id = db_connection.execute(query, params)
        return new_event_id
    except Exception as e:
        logger.error(f"An error occurred: {e}")
