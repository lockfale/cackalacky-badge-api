import logging
import random
from dataclasses import dataclass
from typing import Optional

from connectors.pgsql import PostgreSQLConnector, nullify

logger = logging.getLogger("s3logger")


@dataclass
class UserAchievementView:
    id: int
    name: str
    points: int
    description: str
    user_has_achievement: str


@dataclass
class Achievement:
    id: int
    name: str
    points: int
    description: str


@dataclass
class StaffMember:
    id: int
    discord_handle: str
    discord_user_id: str


class Achievements:
    _RICK_ROLLED = Achievement(id=1, name="Rick Rolled", points=1, description="IYKYK")

    _AROUND_THE_WORLD = Achievement(id=2, name="Around the World", points=10, description="Played all of the games at least once.")

    _SERIAL_PORT_INTERACTION = Achievement(id=3, name="Serial Port Interaction", points=5, description="Interacted with the badge serial port")

    _SECRET_FLAG = Achievement(id=4, name="Secret Flag", points=10, description="Discovered the secret flag")

    _BADGE_ACCESS_POINT = Achievement(id=5, name="Badge Access Point", points=10, description="Enabled the badge access point")

    _BADGE_WEB_AUTH = Achievement(id=6, name="Badge Web Authentication", points=10, description="Unlocked web authentication with the badge")

    _FLAG_TEXT = Achievement(id=7, name="Flag Text", points=10, description="Flag Text")

    _HELLO_WORLD = Achievement(id=8, name="Hello World", points=5, description="Ahh... the classic.")

    # Property decorators to access the private attributes
    @property
    def RICK_ROLLED(self):
        return self._RICK_ROLLED

    @property
    def AROUND_THE_WORLD(self):
        return self._AROUND_THE_WORLD

    @property
    def SERIAL_PORT_INTERACTION(self):
        return self._SERIAL_PORT_INTERACTION

    @property
    def SECRET_FLAG(self):
        return self._SECRET_FLAG

    @property
    def BADGE_ACCESS_POINT(self):
        return self._BADGE_ACCESS_POINT

    @property
    def BADGE_WEB_AUTH(self):
        return self._BADGE_WEB_AUTH

    @property
    def FLAG_TEXT(self):
        return self._FLAG_TEXT

    @property
    def HELLO_WORLD(self) -> Achievement:
        return self._HELLO_WORLD


def get_random_staff_member(db_connection: PostgreSQLConnector) -> Optional[StaffMember]:
    query = """
    select id, discord_handle, discord_user_id from staff;
    """

    try:
        staff_df = db_connection.select_dataframe(query)
        if len(staff_df) == 0:
            return None

        random_staff = random.randint(1, len(staff_df))
        user_dict = staff_df.to_dict("records")[random_staff - 1]
        return StaffMember(id=user_dict["id"], discord_handle=user_dict["discord_handle"], discord_user_id=user_dict["discord_user_id"])
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None


def get_achievement_by_ctf_id_and_user_id(db_connection: PostgreSQLConnector, user_id: int, ctf_id: int) -> Optional[UserAchievementView]:
    query = """
    SELECT ach.id,
               name,
               points,
               description,
               case when ua.user_id is not null then 1 else 0 end as user_has_achievement
        FROM cackalacky.achievements ach
        LEFT JOIN cackalacky.user_achievements ua ON ua.achievement_id = ach.id AND ua.user_id = %(user_id)s
        where ach.id = %(ctf_id)s;
    """

    params = {"user_id": user_id, "ctf_id": ctf_id}

    try:
        achievement_df = db_connection.select_dataframe(query, params)
        if len(achievement_df) == 0:
            return None

        user_dict = achievement_df.to_dict("records")[0]
        return UserAchievementView(
            id=user_dict["id"],
            name=user_dict["name"],
            points=user_dict["points"],
            description=user_dict["description"],
            user_has_achievement=user_dict["user_has_achievement"],
        )
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None


def insert_user_achievement(db_connection: PostgreSQLConnector, user_id: int, achievement_id: int):
    query = f"""
    INSERT INTO cackalacky.user_achievements (user_id, achievement_id) VALUES (%(user_id)s, %(achievement_id)s) RETURNING id;
    """

    params = {"user_id": nullify(user_id), "achievement_id": nullify(achievement_id)}

    try:
        new_user_achievement_id = db_connection.execute(query, params)
        return new_user_achievement_id
    except Exception as e:
        logger.error(f"An error occurred: {e}")
