import pandas as pd
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from common_utils.logger import create_logger

from src.telegram.callbacks.settings import UserSettings
from src.telegram.callbacks.favorites import FavoritesHandler


class MessageHandler:
    log = create_logger("Message Handler")
    thumbnail_dir = 'data/temp_thumbs'
    title_emoji = {
        'alle': '🍲',
        'vegetarisch': '🥦',
        'vegan': '🌱',
        'protein': '🍗',
    }
    meal_types = {
        'alle': '',
        'vegetarisch': 'vegetarische ',
        'vegan': 'vegane ',
        'protein': 'proteinreiche ',
    }

    def __init__(self, options_handler, meal_manager, bot):
        self.settings_handler = options_handler
        self.meal_manager = meal_manager
        self.bot = bot
        # persistent data
        self.last_sent_recipes_df = {}
        self.favorite_handler = FavoritesHandler()

    def send_meals_message(
            self,
            chat_id: int,
            num_meals: int,
            previous_shopping_list_message_id: int | None = None,
            recipes_to_send: pd.DataFrame | None = None,
            recipe_idx_to_replace: int | None = None,
    ):
        """
        Sends the meal recipes and shopping list to the user.

        Args:
            chat_id: The chat ID of the user.
            num_meals: The number of meals to send.
            previous_shopping_list_message_id: The message ID of the previous message (optional).
            recipes_to_send: The recipes to send (optional).
            recipe_idx_to_replace: The index of the recipe to replace (optional).
        """
        if num_meals == 0:
            return

        user_settings = self.settings_handler.get_user_settings(chat_id)

        if recipes_to_send is None:
            recipes_to_send = self.meal_manager.sample_recipes_filtered_by_user_settings(
                num_recipes=num_meals,
                user_settings=user_settings,
            )

        self.last_sent_recipes_df[str(chat_id)] = recipes_to_send

        shopping_list_ingredients = self.meal_manager.get_ingredients_shopping_list(
            recipes_df=recipes_to_send,
            num_portions=user_settings.portions
        )
        shopping_list_message = self.send_shopping_list_message(
            chat_id=chat_id,
            previous_message_id=previous_shopping_list_message_id,
            num_meals=num_meals,
            shopping_list_ingredients=shopping_list_ingredients,
            user_settings=user_settings,
        )

        recipes_pdf_paths = self.meal_manager.get_pdf_paths_from_recipes(
            recipes=recipes_to_send,
            num_portions=user_settings.portions
        )
        recipe_ids = recipes_to_send['id'].tolist()

        user_favorites_ids = self.favorite_handler.get_favorites(chat_id)

        if recipe_idx_to_replace is not None:
            self.send_single_recipe_pdf(
                chat_id=chat_id,
                recipe_pdf_path=recipes_pdf_paths[recipe_idx_to_replace],
                shopping_list_message_id=shopping_list_message.message_id,
                recipe_id=recipe_ids[recipe_idx_to_replace],
                favorites=user_favorites_ids,
            )
        else:
            self.send_recipe_pdfs(
                chat_id=chat_id,
                shopping_list_message_id=shopping_list_message.message_id,
                recipes_pdf_paths=recipes_pdf_paths,
                recipe_ids=recipe_ids,
                user_favorites=user_favorites_ids,
            )

    def send_shopping_list_message(
            self,
            chat_id: int,
            num_meals: int,
            shopping_list_ingredients: str,
            user_settings: UserSettings,
            previous_message_id: int | None,
    ) -> types.Message:
        """
        Sends a message with the combined shopping list for the selected recipes.

        Args:
            chat_id: The chat ID of the user.
            previous_message_id: The message ID of the previous message to replace (optional).
            num_meals: The number of meals to send.
            shopping_list_ingredients: The ingredients for the shopping list.
            user_settings: The user settings for the meal.
        """

        shopping_list_title = self._get_title_response(num_meals, user_settings.meal_type, user_settings.portions)
        shopping_list_message = f"{shopping_list_title}```\n{shopping_list_ingredients}```"
        shopping_list_message_args = {
            'text': shopping_list_message,
            'chat_id': chat_id,
            'parse_mode': 'Markdown',
            'reply_markup': InlineKeyboardMarkup()
        }
        shopping_list_message = self.send_or_edit_message(shopping_list_message_args, previous_message_id)
        return shopping_list_message

    def send_recipe_pdfs(
            self,
            chat_id: int,
            recipes_pdf_paths: list[str],
            recipe_ids: list[int],
            shopping_list_message_id: int | None = None,
            user_favorites: list[str] | None = None,
    ) -> list[int]:
        """
        Send all recipe PDFs to the user.

        Args:
            chat_id: The chat ID of the user.
            recipes_pdf_paths: The paths to the recipe PDFs.
            recipe_ids: The IDs of the recipes.
            shopping_list_message_id: The message id of the shopping list.
            user_favorites: A list of favorite recipe IDs (optional).

        Returns:
            pdf_message_ids: A list of message IDs for the sent PDFs.
        """

        pdf_message_ids = []
        for idx, recipe_pdf_path in enumerate(recipes_pdf_paths):
            pdf_message_id = self.send_single_recipe_pdf(
                chat_id=chat_id,
                recipe_pdf_path=recipe_pdf_path,
                shopping_list_message_id=shopping_list_message_id,
                recipe_id=recipe_ids[idx],
                favorites=user_favorites,
            )
            pdf_message_ids.append(pdf_message_id)

        return pdf_message_ids

    def send_single_recipe_pdf(
            self,
            chat_id: int,
            recipe_pdf_path: str,
            shopping_list_message_id: int,
            recipe_id: int,
            favorites: list[str],
    ) -> int:
        """
        Send a single recipe PDF to the user.

        Args:
            chat_id: The chat ID of the user.
            recipe_pdf_path: The path to the recipe PDF.
            shopping_list_message_id: The message id of the shopping list.
            recipe_id: The ID of the recipe.

        Returns:
            message_id: The message ID of the sent PDF.
        """
        keyboard = self._create_pdf_inline_keyboard(
            shopping_list_message_id=shopping_list_message_id,
            recipe_id=recipe_id,
            favorites=favorites,
        )
        thumb_file = None
        try:
            thumbnail_filename = recipe_pdf_path.split('/')[-1].replace('.pdf', '.jpg')
            thumbnail_path = f'{self.thumbnail_dir}/{thumbnail_filename}'
            try:
                thumb_file = open(thumbnail_path, 'rb')
            except FileNotFoundError:
                self.log.debug(f"Thumbnail not found: {thumbnail_path}")
                thumb_file = None
            with open(recipe_pdf_path, 'rb') as recipe_pdf_file:
                message = self.bot.send_document(
                    chat_id=chat_id,
                    document=recipe_pdf_file,
                    reply_markup=keyboard,
                    thumb=thumb_file if thumb_file else None,
                )
                return message.message_id
        except FileNotFoundError:
            self.log.error(f"PDF not found: {recipe_pdf_path}")
            message = self.bot.send_message(chat_id=chat_id, text="PDF nicht gefunden!", reply_markup=keyboard)
            return message.message_id
        finally:
            if thumb_file:
                thumb_file.close()

    def _create_pdf_inline_keyboard(
            self,
            shopping_list_message_id: int,
            recipe_id: int,
            favorites: list[str],
    ) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup()
        replace_button = InlineButton(
            text='🔄 Austauschen',
            callback_data=f'replace|{shopping_list_message_id}|{recipe_id}'
        )

        is_favorited = recipe_id in favorites
        favorite_button = InlineButton(
            text='⭐️ Speichern' if not is_favorited else '❌ Unfavorisieren',
            callback_data=f'favorite|{recipe_id}' if not is_favorited else f'unfavorite|{recipe_id}',
        )
        keyboard.row(replace_button, favorite_button)

        return keyboard

    def _get_title_response(self, num_meals: int, meal_type: str, portions: int) -> str:
        """
        Generate the title response for the meal message.
        """
        emoji = self.title_emoji.get(meal_type, '🍲')
        friendly_meal_type = self.meal_types.get(meal_type, '')
        title_response = (
            f"**{emoji} Hier sind die Zutaten für {num_meals} {friendly_meal_type}Gerichte á {portions} Portionen:**\n"
        )
        return title_response

    def send_or_edit_message(self, message_args: dict[str, str], message_to_edit_id: int | None = None):
        """
        Sends a new message, or edits a previous message if a message ID is provided.
        """
        if message_to_edit_id:
            ingredient_msg = self.bot.edit_message_text(message_id=message_to_edit_id, **message_args)
        else:
            ingredient_msg = self.bot.send_message(**message_args)
        return ingredient_msg

    def resend_messages_to_replace_meal(
            self,
            message: types.Message,
            related_shopping_list_message_id: int,
            recipe_id: str,
    ):
        # TODO: we need to store each recipe global index in the callback to replace it. This way
        # we can delete the single message, update the shopping list and only sent the new recipe
        chat_id = message.chat.id
        last_sent_recipes = self.last_sent_recipes_df[str(chat_id)]
        updated_recipes, replaced_idx = self.replace_single_recipe_in_data(
            last_sent_recipes=last_sent_recipes,
            chat_id=chat_id,
            recipe_id=recipe_id,
        )

        self.bot.delete_message(chat_id=chat_id, message_id=message.message_id)

        self.send_meals_message(
            chat_id=chat_id,
            num_meals=len(updated_recipes),
            previous_shopping_list_message_id=related_shopping_list_message_id,
            recipes_to_send=updated_recipes,
            recipe_idx_to_replace=replaced_idx,
        )

    def replace_single_recipe_in_data(
            self,
            last_sent_recipes: pd.DataFrame,
            chat_id: int,
            recipe_id: str,
    ) -> tuple[pd.DataFrame, int]:
        user_settings = self.settings_handler.get_user_settings(chat_id)
        new_recipe = self.meal_manager.sample_recipes_filtered_by_user_settings(
            num_recipes=1,
            user_settings=user_settings
        )
        # find the recipe idx to replace
        idx_to_replace = last_sent_recipes.index[last_sent_recipes['id'] == recipe_id].tolist()[0]
        last_sent_recipes.loc[idx_to_replace] = new_recipe.iloc[0]
        return last_sent_recipes, idx_to_replace


