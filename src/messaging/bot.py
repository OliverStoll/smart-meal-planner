import os

import telebot
from dotenv import load_dotenv
import time
from logs.logs import create_logger

from database.engine import recipes_from_sql
from messaging.callbacks.favorites import (
    get_favorite_ids,
    favorize_recipe,
    unfavorize_recipe,
)
from messaging.callbacks.settings import (
    get_setting_options_menu,
    get_user_settings,
    handle_setting_user_setting_option,
    setting_value_confirmation_message,
    recipe_filter_confirmation_message,
)
from settings import DEBUG, RESTART_TIME
from messaging.keyboard import create_settings_keyboard, enumerated_keyboard
from messaging.recipes import sample_recipes, recipe_titles_by_id, recipes_by_id
from src.messaging.callbacks.subscriptions import (
    SubscriptionHandler,
    set_user_subscription,
)
from messaging import CALLBACK_DELIM, MESSAGE_SETTING_CONFIGS
from messaging.messaging import send_full_message, resend_messages_to_replace_meal

log = create_logger("Telegram Meal Bot")
INTRO_RESPONSE = (
    "**🥦 Willkommen beim Kochideen-Bot!**\n\n"
    "Hier kannst du dir mehrere Rezepte für die Woche, mit einer übersichtlichen Einkaufsliste zusenden lassen.\n\n"
    "Um loszulegen, passe mit /einstellungen deine Präferenzen an, lasse dir mit /gerichte eine beliebige Anzahl"
    " an Rezepten zusenden, oder melde dich mit /woechentlich für eine wöchentliche Rezeptliste an.\n\n"
    "Viel Spaß beim Kochen! 🍳🍝"
)
SETTINGS_RESPONSE = "⚙️ Hier kannst du deine Einstellungen anpassen: "
MEALS_RESPONSE = "🍽️ Wie viele Gerichte möchtest du?"
WEEKLY_RESPONSE = "📅 Wie viele Gerichte möchtest du wöchentlich (Montags) erhalten?"
FAVORITE_RESPONSE = "⭐️ Wie viele favorisierte Rezepte möchtest du?"


def log_incoming_msg(message):
    log.debug(f"[{message.chat.username}] Received message: {message.text}")


def register_callback(bot: telebot.TeleBot, prefix: str):
    def decorator(function):
        bot.callback_query_handler(func=lambda call: call.data.startswith(prefix))(function)
        return function

    return decorator


def clean_call_data(call_data: str, prefix: str) -> list[str]:
    call_data = call_data[len(prefix + CALLBACK_DELIM) :]  # noqa
    return call_data.split(CALLBACK_DELIM)


def log_incoming_call(call):
    log.debug(f"[{call.message.chat.username}] Received callback query: {call.data}")


class TelegramBot:
    settings_keyboard = create_settings_keyboard()

    def __init__(self):
        load_dotenv()
        self.bot = telebot.TeleBot(os.environ["TELEGRAM_BOT_TOKEN"])
        self.subscriptions_handler = SubscriptionHandler(bot=self.bot)
        self.setup_message_handlers()
        self.setup_message_callbacks()

    def start_bot_persistent(self) -> None:
        """Start the bot in a loop, restarting it if it crashes."""
        log.info("Starting Bot in a loop!")
        self.subscriptions_handler.schedule_weekly_meal_plans()
        while True:
            self.start_bot()
            time.sleep(RESTART_TIME)
            log.info("Restarting Bot!")

    def start_bot(self) -> None:
        log.info("Starting Bot!")
        try:
            self.bot.polling()
        except Exception as e:
            log.error(f"Error (restarting bot in {RESTART_TIME}): {e}")
            if DEBUG:
                raise e

    def setup_message_handlers(self):
        """Add all message handlers to the bot."""

        @self.bot.message_handler(commands=["start", "help"])
        def send_intro(message):
            log_incoming_msg(message)
            self.bot.send_message(chat_id=message.chat.id, text=INTRO_RESPONSE, parse_mode="Markdown")

        @self.bot.message_handler(commands=["optionen", "options", "einstellungen", "settings"])
        def change_options(message):
            log_incoming_msg(message)
            self.bot.send_message(
                chat_id=message.chat.id,
                text=SETTINGS_RESPONSE,
                reply_markup=self.settings_keyboard,
            )

        @self.bot.message_handler(commands=["gerichte"])
        def send_meal(message):
            log_incoming_msg(message)
            keyboard = enumerated_keyboard(callback_prefix="gerichte", start_idx=1, end_idx=6)
            self.bot.send_message(chat_id=message.chat.id, text=MEALS_RESPONSE, reply_markup=keyboard)

        @self.bot.message_handler(commands=["woechentlich"])
        def send_weekly(message):
            log_incoming_msg(message)
            keyboard = enumerated_keyboard(callback_prefix="woechentlich", start_idx=1, end_idx=6)
            self.bot.send_message(chat_id=message.chat.id, text=WEEKLY_RESPONSE, reply_markup=keyboard)

        @self.bot.message_handler(commands=["favoriten"])
        def send_favorites(message):
            log_incoming_msg(message)
            favorite_ids = get_favorite_ids(chat_id=message.chat.id)
            num_options = min(6, len(favorite_ids))
            keyboard = enumerated_keyboard(callback_prefix="fav_gerichte", start_idx=1, end_idx=num_options)
            self.bot.send_message(chat_id=message.chat.id, text=FAVORITE_RESPONSE, reply_markup=keyboard)

    def setup_message_callbacks(self):
        """Add all callback query handlers to the bot."""

        @register_callback(self.bot, "settings")
        def handle_settings_menu(call):
            log_incoming_call(call)
            setting_name = clean_call_data(call.data, "settings")[0]
            text, reply_markup = get_setting_options_menu(setting_name=setting_name)
            if not text or not reply_markup:
                log.warning(f"Invalid setting name: {setting_name}")
                return
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=reply_markup,
            )

        @register_callback(self.bot, "option")
        def handle_setting_value_set(call):
            log_incoming_call(call)
            call_data = clean_call_data(call.data, prefix="option")
            chat_id = call.message.chat.id
            if len(call_data) != 2:
                log.warning(f"Invalid callback data format: {call.data}, expected 2 args")
                return
            setting_name, value = call_data
            handle_setting_user_setting_option(name=setting_name, value=value, chat_id=chat_id)
            response = setting_value_confirmation_message(setting_name=setting_name, value=value)
            if MESSAGE_SETTING_CONFIGS[setting_name].is_filter:
                response += recipe_filter_confirmation_message(chat_id=chat_id)
            self.bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=response)

        @register_callback(self.bot, "woechentlich")
        def handle_weekly(call):
            log_incoming_call(call)
            chat_id = call.message.chat.id
            call_data = clean_call_data(call.data, prefix="woechentlich")
            num_meals = int(call_data[0])
            response = f"📅 Du hast dich für {num_meals} Gerichte pro Woche angemeldet!"
            set_user_subscription(chat_id, num_meals)
            self.bot.send_message(chat_id=chat_id, text=response)

        @register_callback(self.bot, "replace")
        def handle_replace_recipe(call):
            log_incoming_call(call)
            try:
                shopping_list_msg_id, recipe_id = clean_call_data(call.data, prefix="replace")
                resend_messages_to_replace_meal(
                    bot=self.bot,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    recipe_id=recipe_id,
                    related_shopping_list_message_id=int(shopping_list_msg_id),
                )
            except (ValueError, IndexError) as e:
                log.warning(f"Invalid 'replace' format: {call.data} - {str(e)}")

        @register_callback(self.bot, "favorite")
        def handle_favorize(call):
            log_incoming_call(call)
            try:
                recipe_id = clean_call_data(call_data=call.data, prefix="favorite")[0]
                favorize_recipe(chat_id=call.message.chat.id, recipe_id=recipe_id)
                recipe_title = recipe_titles_by_id(recipes=recipes_from_sql(), recipe_ids=[recipe_id])[0]
                answer_text = f"⭐️ {recipe_title:30} wurde favorisiert"
                self.bot.answer_callback_query(callback_query_id=call.id, text=answer_text)
            except (ValueError, IndexError) as e:
                log.warning(f"Invalid 'favorite' format: {call.data} - {str(e)}")

        @register_callback(self.bot, "unfavorite")
        def handle_unfavorize(call):
            log_incoming_call(call)
            try:
                recipe_id = clean_call_data(call_data=call.data, prefix="unfavorite")[0]
                unfavorize_recipe(chat_id=call.message.chat.id, recipe_id=recipe_id)
                recipe_title = recipe_titles_by_id(recipes=recipes_from_sql(), recipe_ids=[recipe_id])[0]
                answer_text = f"❌ {recipe_title:30} wurde unfavorisiert"
                self.bot.answer_callback_query(callback_query_id=call.id, text=answer_text)
            except (ValueError, IndexError) as e:
                log.warning(f"Invalid 'unfavorite' format: {call.data} - {str(e)}")

        @register_callback(self.bot, "gerichte")
        def handle_meals(call):
            log_incoming_call(call)
            try:
                call_data = clean_call_data(call_data=call.data, prefix="gerichte")
                num_meals = int(call_data[0])
                send_full_message(
                    bot=self.bot,
                    chat_id=call.message.chat.id,
                    previous_shopping_list_message_id=call.message.message_id,
                    num_meals=num_meals,
                )
            except ValueError as e:
                log.warning(f"Invalid 'gerichte' value: {call.data} - {str(e)}")

        @register_callback(self.bot, "fav_gerichte")
        def handle_favorite_meals(call):
            log_incoming_call(call)
            try:
                chat_id = call.message.chat.id
                call_data = clean_call_data(call_data=call.data, prefix="fav_gerichte")
                num_recipes = int(call_data[0])
                user_settings = get_user_settings(chat_id=chat_id)
                favorite_recipe_ids = get_favorite_ids(chat_id=chat_id)
                if not favorite_recipe_ids:
                    self.bot.answer_callback_query(callback_query_id=call.id, text="No favorite recipes found.")
                recipes_df = recipes_by_id(recipes_from_sql(), recipe_ids=favorite_recipe_ids)
                sampled_recipes = sample_recipes(
                    num_recipes=num_recipes,
                    user_settings=user_settings,
                    recipes=recipes_df,
                )
                send_full_message(bot=self.bot, chat_id=chat_id, recipes_to_send=sampled_recipes)
            except ValueError as e:
                log.warning(f"Invalid 'fav_gerichte' value: {call.data} - {str(e)}")

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_all_other_callbacks(call):
            """Handle all other callbacks that don't match any specific handler."""
            log_incoming_call(call)
            log.warning(f"Unhandled callback query: {call.data}")


if __name__ == "__main__":
    TelegramBot().start_bot_persistent(
        #         debug=True
    )
