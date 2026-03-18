from logs.logs import create_logger

from settings import NOSQL_FAVORITES_REF
from database.nosql import nosql_client

log = create_logger("Favorites Handler")


def favorize_recipe(chat_id: int, recipe_id: str):
    ref = f"{NOSQL_FAVORITES_REF}/{chat_id}/{recipe_id}"
    nosql_client().set(ref=ref, data={"favorite": True})


def unfavorize_recipe(chat_id: int, recipe_id: str):
    ref = f"{NOSQL_FAVORITES_REF}/{chat_id}/{recipe_id}/favorite"
    nosql_client().delete(ref=ref)


def get_favorite_ids(chat_id: int) -> list[str]:
    ref = f"{NOSQL_FAVORITES_REF}/{chat_id}"
    favorites = nosql_client().get(ref=ref)
    favorites_ids = [int(key) for key in favorites.keys()] if favorites else []
    return favorites_ids
