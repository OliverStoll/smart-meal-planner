from database.nosql import nosql_client
from settings import NOSQL_USER_DATA_REF


def set_user_setting(chat_id: int, setting_name: str, setting_option: str | int):
    """Sets a specific user setting in the Firebase database."""
    ref = f"{NOSQL_USER_DATA_REF}/{chat_id}/{setting_name}"
    nosql_client().set(
        ref=ref,
        data={"value": setting_option},
    )
