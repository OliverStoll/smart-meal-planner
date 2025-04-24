import json

from common_utils.config import secret
from common_utils.logger import create_logger
from common_utils.apis.firebase import FirebaseClient


class FavoritesHandler:
    log = create_logger("Favorites Handler")
    favorites_path = 'data/favorites.json'
    favorites_ref = 'AppData/Telegram Meal Bot/Favorites'
    firebase_client = FirebaseClient(realtime_db_url=secret('FIREBASE_REALTIME_DB_URL'))

    def favorize_recipe(self, chat_id: int, recipe_id: str):
        """
        Saves a recipe as a favorite for a user in the Firebase database.

        Args:
            chat_id (int): The chat ID of the user.
            recipe_id (str): The ID of the recipe to be saved as a favorite.
        """

        ref = f"{self.favorites_ref}/{chat_id}/{recipe_id}"
        self.firebase_client.set_entry(
            ref=ref,
            data={'favorite': True},
        )

    def unfavorize_recipe(self, chat_id: int, recipe_id: str):
        """
        Removes a recipe from the user's favorites in the Firebase database.

        Args:
            chat_id (int): The chat ID of the user.
            recipe_id (str): The ID of the recipe to be removed from favorites.
        """

        ref = f"{self.favorites_ref}/{chat_id}/{recipe_id}/favorite"
        self.firebase_client.delete_entry(ref=ref)

    def get_favorites(self, chat_id: int) -> list[str]:
        """
        Retrieves the list of favorite recipes for a user from the Firebase database.

        Args:
            chat_id (int): The chat ID of the user.

        Returns:
            A list containing the user's favorite recipe ids.
        """

        ref = f"{self.favorites_ref}/{chat_id}"
        favorites = self.firebase_client.get_entry(ref=ref)
        favorites_ids = list(favorites.keys()) if favorites else []
        return favorites_ids
