import pandas as pd
from telebot import types, TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from common_utils.logger import create_logger
from PIL import Image
from io import BytesIO

import messaging.ingredients
from database.engine import recipes_from_sql
from messaging.callbacks.settings_types import UserSettings
from messaging.recipes import sample_recipes


class MessageHandler:
    log = create_logger("Message Handler")
    title_emoji = {
        "alle": "🍲",
        "vegetarisch": "🥦",
        "vegan": "🌱",
        "protein": "🍗",
    }
    meal_types = {
        "alle": "",
        "vegetarisch": "vegetarische ",
        "vegan": "vegane ",
        "protein": "proteinreiche ",
    }

    def __init__(self, settings_handler, favorites_handler, bot):
        self.settings_handler = settings_handler
        self.favorite_handler = favorites_handler
        self.bot = bot
        # persistent data
        self.last_sent_recipes_df = {}
        self.pdf_handler = PdfMessageHandler(bot=bot, recipes=recipes_from_sql())

    def send_full_recipes_message(
        self,
        chat_id: int,
        num_meals: int | None = None,
        previous_shopping_list_message_id: int | None = None,
        recipes_to_send: pd.DataFrame | None = None,
        recipe_idx_to_replace: int | None = None,
    ):
        """
        Sends the meal recipes and shopping list to the user.

        Args:
            chat_id: The chat ID of the user.
            num_meals: The number of meals to send. Not required if recipes_to_send is provided.
            previous_shopping_list_message_id: The message ID of the previous message (optional).
            recipes_to_send: The recipes to send (optional).
            recipe_idx_to_replace: The index of the recipe to replace (optional).
        """

        if num_meals == 0:
            self.log.info("No meals requested, not sending any messages.")
            return
        if recipes_to_send is None and num_meals is None:
            self.log.error("Either recipes_to_send or num_meals must be provided.")
            return

        num_meals = num_meals or len(recipes_to_send)
        user_settings = self.settings_handler.get_user_settings(chat_id=chat_id)

        if recipes_to_send is None:
            recipes_to_send = sample_recipes(
                num_recipes=num_meals,
                user_settings=user_settings,
            )
        recipe_ids = recipes_to_send["id"].tolist()
        self.last_sent_recipes_df[str(chat_id)] = recipes_to_send

        shopping_list_ingredients = messaging.ingredients.ingredients_shopping_list(
            recipes=recipes_to_send, num_portions=user_settings.portions
        )
        shopping_list_message = self.send_shopping_list_message(
            chat_id=chat_id,
            num_meals=num_meals,
            user_settings=user_settings,
            replace_message_id=previous_shopping_list_message_id,
            shopping_list_ingredients=shopping_list_ingredients,
        )

        favorites_ids = self.favorite_handler.get_favorites(chat_id)

        if recipe_idx_to_replace is not None:
            recipe_id = recipe_ids[recipe_idx_to_replace]
            self.pdf_handler.send_single_recipe_pdf(
                chat_id=chat_id,
                num_portions=user_settings.portions,
                shopping_list_message_id=shopping_list_message.message_id,
                recipe_id=recipe_id,
                is_favorite=recipe_id in favorites_ids,
            )
        else:
            self.pdf_handler.send_multiple_recipe_pdfs(
                chat_id=chat_id,
                recipe_ids=recipe_ids,
                num_portions=user_settings.portions,
                shopping_list_message_id=shopping_list_message.message_id,
                favorites_ids=favorites_ids,
            )

    def resend_messages_to_replace_meal(
        self,
        message_id: int,
        chat_id: int,
        related_shopping_list_message_id: int,
        recipe_id: str,
    ):
        last_sent_recipes: pd.DataFrame | None = self.last_sent_recipes_df.get(
            str(chat_id), None
        )

        if last_sent_recipes is None:
            raise ValueError(f"No recipes found for chat ID {chat_id}.")

        updated_recipes, replaced_idx = self.replace_single_recipe_in_data(
            last_sent_recipes=last_sent_recipes,  # noqa
            chat_id=chat_id,
            recipe_id=recipe_id,
        )

        self.bot.delete_message(chat_id=chat_id, message_id=message_id)

        self.send_full_recipes_message(
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
        new_recipe = sample_recipes(num_recipes=1, user_settings=user_settings)
        # find the recipe idx to replace
        idx_to_replace = last_sent_recipes.index[
            last_sent_recipes["id"] == recipe_id
        ].tolist()[0]
        last_sent_recipes.loc[idx_to_replace] = new_recipe.iloc[0]
        return last_sent_recipes, idx_to_replace

    def send_shopping_list_message(
        self,
        chat_id: int,
        num_meals: int,
        shopping_list_ingredients: str,
        user_settings: UserSettings,
        replace_message_id: int | None,
    ) -> types.Message:
        """
        Sends a message with the combined shopping list for the selected recipes.

        Args:
            chat_id: The chat ID of the user.
            replace_message_id: The message ID of the previous message to replace (optional).
            num_meals: The number of meals to send.
            shopping_list_ingredients: The ingredients for the shopping list.
            user_settings: The user settings for the meal.
        """

        shopping_list_title = self._get_shopping_list_title(
            num_meals, user_settings.meal_type, user_settings.portions
        )
        shopping_list_message = (
            f"{shopping_list_title}\n```\n{shopping_list_ingredients}```"
        )
        shopping_list_message_args = {
            "text": shopping_list_message,
            "chat_id": chat_id,
            "parse_mode": "Markdown",
        }
        if replace_message_id:
            sent_message = self.bot.edit_message_text(
                message_id=replace_message_id, **shopping_list_message_args
            )
        else:
            sent_message = self.bot.send_message(**shopping_list_message_args)
        return sent_message

    def _get_shopping_list_title(
        self, num_meals: int, meal_type: str, portions: int
    ) -> str:
        """
        Generate the title response for the meal message.
        """
        emoji = self.title_emoji.get(meal_type, "🍲")
        friendly_meal_type = self.meal_types.get(meal_type, "")
        title_response = f"**{emoji} Hier sind die Zutaten für {num_meals} {friendly_meal_type}Gerichte á {portions} Portionen:**"
        return title_response


class PdfMessageHandler:
    log = create_logger("PDF Message Handler")
    thumbnail_dir = "data/temp_thumbs"
    recipe_pdf_dir = "data/temp_pdfs"
    pdf_id_to_title_mapping = {}

    def __init__(self, bot: TeleBot, recipes: pd.DataFrame):
        self.bot = bot
        self.pdf_id_to_title_mapping = self._get_pdf_id_to_title_mapping(recipes)

    def send_multiple_recipe_pdfs(
        self,
        chat_id: int,
        recipe_ids: list[int],
        num_portions: int,
        shopping_list_message_id: int | None = None,
        favorites_ids: list[str] | None = None,
    ) -> list[int]:
        """
        Send all recipe PDFs to the user.

        Args:
            chat_id: The chat ID of the user.
            recipe_ids: The IDs of the recipes.
            num_portions: The number of portions.
            shopping_list_message_id: The message id of the shopping list.
            favorites_ids: A list of favorite recipe IDs (optional).

        Returns:
            pdf_message_ids: A list of message IDs for the sent PDFs.
        """

        pdf_message_ids = []
        for idx, recipe_id in enumerate(recipe_ids):
            is_favorite = recipe_id in favorites_ids if favorites_ids else False
            pdf_message_id = self.send_single_recipe_pdf(
                chat_id=chat_id,
                shopping_list_message_id=shopping_list_message_id,
                recipe_id=recipe_id,
                num_portions=num_portions,
                is_favorite=is_favorite,
            )
            pdf_message_ids.append(pdf_message_id)

        return pdf_message_ids

    def send_single_recipe_pdf(
        self,
        chat_id: int,
        recipe_id: int,
        num_portions: int,
        shopping_list_message_id: int | None = None,
        is_favorite: bool = False,
    ) -> int:
        """
        Send a single recipe PDF to the user.

        Args:
            chat_id: The chat ID of the user.
            shopping_list_message_id: The message id of the shopping list.
            recipe_id: The ID of the recipe.
            num_portions: The number of portions.
            is_favorite: Whether the recipe is a favorite (optional).

        Returns:
            message_id: The message ID of the sent PDF.
        """
        thumbnail_file = self._get_thumbnail_file(recipe_id=recipe_id)
        recipe_pdf_path = self._get_pdf_ref(
            recipe_id=recipe_id, num_portions=num_portions
        )
        keyboard = self._create_pdf_inline_keyboard(
            shopping_list_message_id=shopping_list_message_id,
            recipe_id=recipe_id,
            is_favorite=is_favorite,
        )

        try:
            with open(recipe_pdf_path, "rb") as recipe_pdf_file:
                message = self.bot.send_document(
                    chat_id=chat_id,
                    document=recipe_pdf_file,
                    reply_markup=keyboard,
                    thumb=thumbnail_file,
                )
                return message.message_id
        except FileNotFoundError:
            self.log.error(f"PDF not found: {recipe_pdf_path}")
            message = self.bot.send_message(
                chat_id=chat_id, text="PDF nicht gefunden!", reply_markup=keyboard
            )
            return message.message_id

    def _get_thumbnail_file(self, recipe_id: int) -> BytesIO | None:
        """
        Get the thumbnail file for the recipe.

        Args:
            recipe_id: The ID of the recipe.

        Returns:
            thumbnail_file: The thumbnail file as a BytesIO object.
        """
        pdf_title = self.pdf_id_to_title_mapping.get(recipe_id, None)
        thumbnail_path = f"{self.thumbnail_dir}/{pdf_title}.jpg"
        if not pdf_title:
            self.log.warning(f"Thumbnail not found for recipe ID {recipe_id}")
            return None
        try:
            img = Image.open(thumbnail_path)
            bytes_io = BytesIO()
            bytes_io.name = f"{pdf_title}.jpg"
            img.save(bytes_io, format="JPEG")
            bytes_io.seek(0)
            return bytes_io
        except FileNotFoundError:
            self.log.error(f"Thumbnail not found: {thumbnail_path}")
            return None

    @staticmethod
    def _create_pdf_inline_keyboard(
        shopping_list_message_id: int | None,
        recipe_id: int,
        is_favorite: bool = False,
    ) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup()
        replace_button = InlineButton(
            text="🔄 Austauschen",
            callback_data=f"replace|{shopping_list_message_id}|{recipe_id}",
        )

        favorite_button = InlineButton(
            text="⭐️ Speichern" if not is_favorite else "❌ Unfavorisieren",
            callback_data=f"favorite|{recipe_id}"
            if not is_favorite
            else f"unfavorite|{recipe_id}",
        )
        keyboard.row(replace_button, favorite_button)

        return keyboard

    def _get_pdf_ref(self, recipe_id: int, num_portions: int) -> str | None:
        """
        Get the path to the PDF file for the recipe.

        Args:
            recipe_id: The ID of the recipe.
            num_portions: The number of portions.

        Returns:
            pdf_path: The path to the PDF file.
        """
        pdf_title = self.pdf_id_to_title_mapping.get(recipe_id, None)
        if not pdf_title:
            self.log.warning(f"PDF not found for recipe ID {recipe_id}")
            return None

        ref = f"pdf/{num_portions}/{pdf_title}.pdf"
        return ref

    @staticmethod
    def _get_pdf_id_to_title_mapping(recipes: pd.DataFrame) -> dict[int, str]:
        """
        Generate a mapping of recipe IDs to PDF paths.
        """
        pdf_id_to_title_mapping = {}
        for idx, recipe in recipes.iterrows():
            pdf_id_to_title_mapping[recipe["id"]] = recipe["title"]
        return pdf_id_to_title_mapping
