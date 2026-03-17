import os
import telebot
from dotenv import load_dotenv
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from common_utils.logger import create_logger

from messaging.recipes import num_of_filtered_recipes, sample_recipes
from src.messaging.messaging import MessageHandler
from src.messaging.callbacks.subscriptions import SubscriptionHandler
from src.messaging.callbacks.settings import SettingsHandler
from src.messaging.callbacks.favorites import FavoritesHandler
from messaging import CALLBACK_DELIM


class TelegramBot:
    log = create_logger("Telegram Meal Bot")
    restart_time = 10
    intro_response = (
        "**🥦 Willkommen beim Kochideen-Bot!**\n\n"
        "Hier kannst du dir mehrere Rezepte für die Woche, mit einer übersichtlichen Einkaufsliste zusenden lassen.\n\n"
        "Um loszulegen, passe mit /einstellungen deine Präferenzen an, lasse dir mit /gerichte eine beliebige Anzahl"
        " an Rezepten zusenden, oder melde dich mit /woechentlich für eine wöchentliche Rezeptliste an.\n\n"
        "Viel Spaß beim Kochen! 🍳🍝"
    )
    settings_keyboard = InlineKeyboardMarkup()
    settings_keyboard.row(
        InlineButton("🍽️ Portionsanzahl", callback_data="settings|portions"),
        InlineButton("🥦 Ernährungsform", callback_data="settings|meal_type"),
    )
    settings_keyboard.row(
        InlineButton("⏱️ Kochzeit", callback_data="settings|max_duration"),
        InlineButton("🔥 Kalorien (min.)", callback_data="settings|cal_min"),
    )

    def __init__(self):
        load_dotenv()
        self.bot = telebot.TeleBot(os.environ["TELEGRAM_BOT_TOKEN"])
        self.settings = SettingsHandler()
        self.favorites_handler = FavoritesHandler()
        self.message_handler = MessageHandler(
            settings_handler=self.settings,
            favorites_handler=self.favorites_handler,
            bot=self.bot,
        )
        self.subscriptions_handler = SubscriptionHandler(
            bot=self.bot, message_handler=self.message_handler
        )
        self.setup_message_handlers()
        self.setup_message_callbacks()

    def start_bot(self, debug: bool = False) -> None:
        """Start the bot in a loop, restarting it if it crashes."""
        self.log.info("Starting Bot in a loop!")
        self.subscriptions_handler.schedule_weekly_meal_plans()
        while True:
            self._start_bot_once(raise_exceptions=debug)
            time.sleep(self.restart_time)
            self.log.info("Restarting Bot!")

    def _start_bot_once(self, raise_exceptions: bool) -> None:
        """Start the bot once and handle exceptions.

        Args:
            raise_exceptions: If True, raise exceptions for debugging.
        """
        self.log.info("Starting Bot!")
        try:
            self.bot.polling()
        except Exception as e:
            self.log.error(f"Error (restarting bot in {self.restart_time}): {e}")
            if raise_exceptions:
                raise e

    def setup_message_handlers(self):
        """Add all message handlers to the bot."""

        @self.bot.message_handler(commands=["start", "help"])
        def send_intro(message):
            _log_incoming_message(message)
            self.bot.send_message(
                chat_id=message.chat.id, text=self.intro_response, parse_mode="Markdown"
            )

        @self.bot.message_handler(
            commands=["optionen", "options", "einstellungen", "settings"]
        )
        def change_options(message):
            _log_incoming_message(message)
            response = "⚙️ Hier kannst du deine Einstellungen anpassen: "
            self.bot.send_message(
                chat_id=message.chat.id,
                text=response,
                reply_markup=self.settings_keyboard,
            )

        @self.bot.message_handler(commands=["gerichte"])
        def send_meal(message):
            _log_incoming_message(message)
            response = "🍽️ Wie viele Gerichte möchtest du?"
            keyboard = _get_enumerated_keyboard(
                callback_prefix="gerichte", start_idx=1, end_idx=6
            )
            self.bot.send_message(
                chat_id=message.chat.id, text=response, reply_markup=keyboard
            )

        @self.bot.message_handler(commands=["woechentlich"])
        def send_weekly(message):
            _log_incoming_message(message)
            response = (
                "📅 Wie viele Gerichte möchtest du wöchentlich (Montags) erhalten?"
            )
            keyboard = _get_enumerated_keyboard(
                callback_prefix="woechentlich", start_idx=1, end_idx=6
            )
            self.bot.send_message(
                chat_id=message.chat.id, text=response, reply_markup=keyboard
            )

        @self.bot.message_handler(commands=["favoriten"])
        def send_favorites(message):
            _log_incoming_message(message)
            favorite_ids = self.favorites_handler.get_favorites(chat_id=message.chat.id)
            num_favorites = len(favorite_ids)
            num_options = min(6, num_favorites)
            response = "⭐️ Wie viele favorisierte Rezepte möchtest du?"
            keyboard = _get_enumerated_keyboard(
                callback_prefix="fav_gerichte", start_idx=1, end_idx=num_options
            )
            self.bot.send_message(
                chat_id=message.chat.id, text=response, reply_markup=keyboard
            )

        def _log_incoming_message(message):
            self.log.debug(
                f"[{message.chat.username}] Received message: {message.text}"
            )

        def _get_enumerated_keyboard(callback_prefix, start_idx, end_idx, delim="|"):
            """Create a keyboard with enumerated buttons."""
            keyboard = InlineKeyboardMarkup()
            buttons = [
                InlineButton(f"{i}", callback_data=f"{callback_prefix}{delim}{i}")
                for i in range(start_idx, end_idx + 1)
            ]
            keyboard.row(*buttons)
            return keyboard

    def setup_message_callbacks(self):
        """Add all callback query handlers to the bot."""

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("settings|")
        )
        def handle_settings_menu(call):
            _log_incoming_callback(call)
            setting_name = call.data.replace("settings|", "")
            setting_options_menu = self.settings.get_setting_options_menu(
                setting_name=setting_name
            )
            if not setting_options_menu:
                self.log.warning(f"Invalid setting name: {setting_name}")
                return
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                **setting_options_menu,
            )

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("option|")
        )
        def handle_settings_option(call):
            _log_incoming_callback(call)
            call_data = call.data.replace("option|", "")
            if call_data.count(CALLBACK_DELIM) != 1:
                self.log.warning(f"Invalid callback data format: {call.data}")
                return
            chat_id = call.message.chat.id
            (
                setting_name,
                setting_option,
            ) = self.settings.handle_setting_user_setting_option(
                call_data=call_data, chat_id=chat_id
            )
            setting_properties = self.settings.get_setting_properties(setting_name)
            response = self.settings.get_setting_option_confirmation_message(
                setting_name=setting_name,
                option_value=setting_option,
            )
            if setting_properties.is_filter:
                user_settings = self.settings.get_user_settings(chat_id=chat_id)
                num_options = num_of_filtered_recipes(user_settings=user_settings)
                response += self.settings.get_complete_filter_confirmation_message(
                    num_meal_options=num_options
                )

            self.bot.edit_message_text(
                chat_id=chat_id, message_id=call.message.message_id, text=response
            )

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("woechentlich|")
        )
        def handle_woechentlich(call):
            _log_incoming_callback(call)
            self.subscriptions_handler.handle_subscription_callback(call)

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("replace|")
        )
        def handle_replace(call):
            _log_incoming_callback(call)
            try:
                _, shopping_list_msg_id_str, recipe_id = call.data.split(CALLBACK_DELIM)
                shopping_list_msg_id = int(shopping_list_msg_id_str)
                message_id, chat_id = call.message.message_id, call.message.chat.id
                self.message_handler.resend_messages_to_replace_meal(
                    recipe_id=recipe_id,
                    message_id=message_id,
                    chat_id=chat_id,
                    related_shopping_list_message_id=shopping_list_msg_id,
                )
            except (ValueError, IndexError) as e:
                self.log.warning(f"Invalid 'replace' format: {call.data} - {str(e)}")

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("favorite|")
        )
        def handle_favorite(call):
            _log_incoming_callback(call)
            try:
                _, recipe_id = call.data.split(CALLBACK_DELIM)
                self.favorites_handler.favorize_recipe(
                    chat_id=call.message.chat.id, recipe_id=recipe_id
                )
                recipe_title = self.recipes.recipe_titles_by_id(recipe_ids=[recipe_id])[
                    0
                ]
                answer_text = f"⭐️ {recipe_title:30} wurde favorisiert"
                self.bot.answer_callback_query(
                    callback_query_id=call.id, text=answer_text
                )
            except (ValueError, IndexError) as e:
                self.log.warning(f"Invalid 'favorite' format: {call.data} - {str(e)}")

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("unfavorite")
        )
        def handle_unfavorite(call):
            _log_incoming_callback(call)
            try:
                _, recipe_id = call.data.split(CALLBACK_DELIM)
                self.favorites_handler.unfavorize_recipe(
                    chat_id=call.message.chat.id, recipe_id=recipe_id
                )
                recipe_title = self.recipes.recipe_titles_by_id(recipe_ids=[recipe_id])[
                    0
                ]
                answer_text = f"❌ {recipe_title:30} wurde unfavorisiert"
                self.bot.answer_callback_query(
                    callback_query_id=call.id, text=answer_text
                )
            except (ValueError, IndexError) as e:
                self.log.warning(f"Invalid 'unfavorite' format: {call.data} - {str(e)}")

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("gerichte")
        )
        def handle_gerichte(call):
            _log_incoming_callback(call)
            try:
                call_data = call.data.replace("gerichte" + CALLBACK_DELIM, "")
                num_meals = int(call_data)
                self.message_handler.send_full_recipes_message(
                    chat_id=call.message.chat.id,
                    previous_shopping_list_message_id=call.message.message_id,
                    num_meals=num_meals,
                )
            except ValueError as e:
                self.log.warning(f"Invalid 'gerichte' value: {call.data} - {str(e)}")

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("fav_gerichte")
        )
        def handle_fav_gerichte(call):
            _log_incoming_callback(call)
            try:
                chat_id = call.message.chat.id
                call_data = call.data.replace("fav_gerichte" + CALLBACK_DELIM, "")
                num_recipes = int(call_data)
                user_settings = self.settings.get_user_settings(chat_id=chat_id)
                favorite_recipe_ids = self.favorites_handler.get_favorites(
                    chat_id=chat_id
                )
                recipes_df = self.recipes.recipes_by_id(recipe_ids=favorite_recipe_ids)
                sampled_recipes = sample_recipes(
                    num_recipes=num_recipes,
                    user_settings=user_settings,
                    recipes=recipes_df,
                )
                self.message_handler.send_full_recipes_message(
                    chat_id=chat_id,
                    recipes_to_send=sampled_recipes,
                )
            except ValueError as e:
                self.log.warning(
                    f"Invalid 'fav_gerichte' value: {call.data} - {str(e)}"
                )

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_all_other_callbacks(call):
            """Handle all other callbacks that don't match any specific handler."""
            _log_incoming_callback(call)
            self.log.warning(f"Unhandled callback query: {call.data}")

        def _log_incoming_callback(call):
            self.log.debug(
                f"[{call.message.chat.username}] Received callback query: {call.data}"
            )


if __name__ == "__main__":
    TelegramBot().start_bot(
        #         debug=True
    )
