import telebot
from os import getenv
import os
import json
from dotenv import load_dotenv
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from common_utils.logger import create_logger

from meals import RecipeManager
from subscriptions.subscriptions import SubscriptionHandler
from settings import SettingsHandler
from messaging import MessageHandler
from favorites import FavoritesHandler


class TelegramBot:
    log = create_logger("Telegram Meal Bot")
    meal_manager = RecipeManager()
    restart_time = 60
    intro_response = (
        f"**🥦 Willkommen beim Kochideen-Bot!**\n\n"
        f"Hier kannst du dir mehrere Rezepte für die Woche, mit einer übersichtlichen Einkaufsliste zusenden lassen. \n\n"
        f"Um loszulegen, passe mit /einstellungen deine Präferenzen an, lasse dir mit /gerichte eine beliebige Anzahl"
        f" an Rezepten zusenden, oder melde dich mit /woechentlich für eine wöchentliche Rezeptliste an.\n\n"
        f"Viel Spaß beim Kochen! 🍳🍝"
    )
    settings_keyboard = InlineKeyboardMarkup()
    settings_keyboard.row(
        InlineButton('🍽️ Portionsanzahl', callback_data='settings|portions'),
        InlineButton('🥦 Ernährungsform', callback_data='settings|meal_type'),
    )
    settings_keyboard.row(
        InlineButton('⏱️ Kochzeit', callback_data='settings|max_duration'),
        InlineButton('🔥 Kalorien (min.)', callback_data='settings|cal_min')
    )

    def __init__(self, secret_env_name='TELEGRAM_BOT_TOKEN'):
        load_dotenv()
        self.bot = telebot.TeleBot(getenv(secret_env_name))
        self.options_handler = SettingsHandler(self.bot, self.meal_manager)
        self.message_handler = MessageHandler(self.options_handler, self.meal_manager, self.bot)
        self.callback_delimiter = self.options_handler.callback_delim
        self.subscriptions_handler = SubscriptionHandler(self.bot, self.message_handler)
        self.favorites_handler = FavoritesHandler()
        self.setup_message_handlers()
        self.setup_message_callbacks()

    def start_bot(self, raise_exceptions: bool = False) -> None:
        """ Start the bot in a loop, restarting it if it crashes. """
        self.log.info("Starting Bot in a loop!")
        self.subscriptions_handler.schedule_weekly_meal_plans()
        while True:
            self._start_bot_once(raise_exceptions=raise_exceptions)
            time.sleep(self.restart_time)
            self.log.info("Restarting Bot!")

    def _start_bot_once(self, raise_exceptions: bool) -> None:
        """ Start the bot once and handle exceptions.

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
        """ Add all message handlers to the bot. """

        @self.bot.message_handler(commands=['start', 'help'])
        def send_intro(message):
            _log_incoming_message(message)
            self.bot.send_message(chat_id=message.chat.id, text=self.intro_response, parse_mode='Markdown')

        @self.bot.message_handler(commands=['optionen', 'options', 'einstellungen', 'settings'])
        def change_options(message):
            _log_incoming_message(message)
            response = "⚙️ Hier kannst du deine Einstellungen anpassen: "
            self.bot.send_message(chat_id=message.chat.id, text=response, reply_markup=self.settings_keyboard)

        @self.bot.message_handler(commands=['gerichte'])
        def send_meal(message):
            _log_incoming_message(message)
            response = "🍽️ Wie viele Gerichte möchtest du?"
            keyboard = InlineKeyboardMarkup()
            buttons = _get_enumerated_buttons(prefix='gerichte', start_idx=1, end_idx=6)
            keyboard.row(*buttons)
            self.bot.send_message(chat_id=message.chat.id, text=response, reply_markup=keyboard)

        @self.bot.message_handler(commands=['woechentlich'])
        def send_weekly(message):
            _log_incoming_message(message)
            response = "📅 Wie viele Gerichte möchtest du wöchentlich (Montags) erhalten?"
            keyboard = InlineKeyboardMarkup()
            buttons = _get_enumerated_buttons(prefix='woechentlich', start_idx=0, end_idx=6)
            keyboard.row(*buttons)
            self.bot.send_message(chat_id=message.chat.id, text=response, reply_markup=keyboard)

        @self.bot.message_handler(commands=['favoriten'])
        def send_favorites(message):
            _log_incoming_message(message)
            favorite_ids = self.favorites_handler.get_favorites(chat_id=message.chat.id)
            favorite_recipes = self.meal_manager.get_recipe_titles(favorite_ids)
            favorite_recipes = sorted(favorite_recipes)
            response = "⭐️ Hier sind deine Favoriten:"
            for recipe in favorite_recipes:
                response += f"\n  - {recipe}"
            self.bot.send_message(chat_id=message.chat.id, text=response)

        def _log_incoming_message(message):
            self.log.debug(f"[{message.chat.username}] Received message: {message.text}")

        def _get_enumerated_buttons(prefix, start_idx, end_idx, delim='|'):
            return [
                InlineButton(f"{i}", callback_data=f'{prefix}{delim}{i}')
                for i in range(start_idx, end_idx + 1)
            ]

    def setup_message_callbacks(self):
        """ Add all callback query handlers to the bot. """

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('settings|'))
        def handle_settings(call):
            _log_incoming_callback(call)
            setting_name = call.data.replace('settings|', '')
            self.options_handler.handle_settings_callback(setting_name, call.message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('option|'))
        def handle_option(call):
            _log_incoming_callback(call)
            call_data = call.data.replace('option|', '')
            self.options_handler.handle_user_setting_callback(call_data, call.message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('woechentlich|'))
        def handle_woechentlich(call):
            _log_incoming_callback(call)
            self.subscriptions_handler.handle_subscription_callback(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('replace|'))
        def handle_replace(call):
            _log_incoming_callback(call)
            try:
                _, msg_id_str, recipe_id = call.data.split(self.callback_delimiter)
                shopping_list_msg_id = int(msg_id_str)
                self.message_handler.resend_messages_to_replace_meal(
                    message=call.message,
                    related_shopping_list_message_id=shopping_list_msg_id,
                    recipe_id=recipe_id
                )
            except (ValueError, IndexError) as e:
                self.log.warning(f"Invalid 'replace' format: {call.data}")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('favorite|'))
        def handle_favorite(call):
            _log_incoming_callback(call)
            try:
                _, recipe_id = call.data.split(self.callback_delimiter)
                self.favorites_handler.favorize_recipe(
                    chat_id=call.message.chat.id,
                    recipe_id=recipe_id
                )
                self.bot.answer_callback_query(callback_query_id=call.id, text="Added to favorites ⭐️")
            except (ValueError, IndexError) as e:
                self.log.warning(f"Invalid 'favorite' format: {call.data}")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('unfavorite'))
        def handle_unfavorite(call):
            _log_incoming_callback(call)
            try:
                _, recipe_id = call.data.split(self.callback_delimiter)
                self.favorites_handler.unfavorize_recipe(
                    chat_id=call.message.chat.id,
                    recipe_id=recipe_id
                )
                self.bot.answer_callback_query(callback_query_id=call.id, text="Removed from favorites ❌")
            except (ValueError, IndexError) as e:
                self.log.warning(f"Invalid 'unfavorite' format: {call.data}")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('gerichte'))
        def handle_gerichte(call):
            _log_incoming_callback(call)
            try:
                call_data = call.data.replace(f'gerichte{self.callback_delimiter}', '')
                num_meals = int(call_data)
                self.message_handler.send_meals_message(
                    chat_id=call.message.chat.id,
                    previous_shopping_list_message_id=call.message.message_id,
                    num_meals=num_meals
                )
            except ValueError:
                self.log.warning(f"Invalid 'gerichte' value: {call.data}")

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_all_other_callbacks(call):
            """ Handle all other callbacks that don't match any specific handler. """
            _log_incoming_callback(call)
            self.log.warning(f"Unhandled callback query: {call.data}")

        def _log_incoming_callback(call):
            self.log.debug(f"[{call.message.chat.username}] Received callback query: {call.data}")


if __name__ == "__main__":
    TelegramBot().start_bot(
        raise_exceptions=True
    )