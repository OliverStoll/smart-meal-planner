import telebot
from os import getenv
import os
import json
from dotenv import load_dotenv
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from utils.logger import create_logger

from meals import HF_Meal_Manager
from subscription_handler import SubscriptionHandler
from settings_handler import SettingsHandler
from message_handler import MessageHandler




class TelegramBot:
    log = create_logger("Telegram Meal Bot")
    meal_manager = HF_Meal_Manager()
    restart_time = 60
    intro_response = (
        f"**Willkommen beim Kochideen-Bot!** 🥦\n\nHier kannst du dir Rezepte für die Woche, "
        f"mit einer übersichtlichen Einkaufsliste zusenden lassen. \n\nUm loszulegen, "
        f"passe mit /optionen deine Einstellungen an, lasse dir mit /gerichte eine "
        f"beliebige Anzahl an Rezepten zusenden, oder melde dich mit /woechentlich für "
        f"eine wöchentliche Rezeptliste an.\n\nViel Spaß beim Kochen! 🍳🍝")

    def __init__(self):
        load_dotenv()
        self.bot = telebot.TeleBot(getenv('TELEGRAM_BOT_TOKEN'))
        self.options_handler = SettingsHandler(self.bot, self.meal_manager)
        self.message_handler = MessageHandler(self.options_handler, self.meal_manager, self.bot)
        self.subscriptions_handler = SubscriptionHandler(self.bot, self.message_handler)
        self.setup_handlers()

    def start_bot(self, debug=False):
        threading.Thread(
            target=self.subscriptions_handler.schedule_weekly_subscription_messages
        ).start()
        while True:
            self.log.info("Starting Bot!")
            try:
                self.bot.polling()
            except Exception as e:
                self.log.error(f"Error (restarting bot in {self.restart_time}): {e}")
                if debug:
                    raise e
            time.sleep(self.restart_time)
            self.log.info("Restarting Bot!")

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_intro(message):
            self.log.debug(f"[{message.chat.username}] Received message: {message.text}")
            self.bot.send_message(chat_id=message.chat.id, text=self.intro_response, parse_mode='Markdown')

        @self.bot.message_handler(commands=['optionen', 'options', 'einstellungen', 'settings'])
        def change_options(message):
            self.log.debug(f"[{message.chat.username}] Received message: {message.text}")
            response = "Hier kannst du deine Einstellungen anpassen:"
            keyboard = InlineKeyboardMarkup()
            keyboard.row(
                InlineButton('Portionsanzahl', callback_data='settings_portions'),
                InlineButton('Art der Gerichte', callback_data='settings_meal-type'),
            )
            keyboard.row(
                InlineButton('Kochzeit', callback_data='settings_max-duration'),
                InlineButton('Kalorien (min.)', callback_data='settings_cal-min')
            )
            self.bot.send_message(chat_id=message.chat.id, text=response, reply_markup=keyboard)

        @self.bot.callback_query_handler(func=lambda call: True)
        def options_callback(call):
            self.log.debug(f"[{call.message.chat.username}] Received callback query: {call.data}")
            if call.data.startswith('settings_'):
                self.options_handler.handle_settings_callback(call)
            elif call.data.startswith('option_'):
                self.options_handler.handle_user_setting_callback(call)
            elif call.data.startswith('gerichte_'):
                num_meals = int(call.data.replace('gerichte_', ''))
                self.message_handler.send_meals_message(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    num_meals=num_meals)
            elif call.data.startswith('woechentlich_'):
                self.subscriptions_handler.handle_subscription_callback(call)
            elif call.data.startswith('replace_'):
                data = call.data.split('_')[1:]
                idx = int(data[0])
                ingredients_msg_id = int(data[1])
                self.message_handler.replace_meal(call, idx, ingredients_msg_id)

        @self.bot.message_handler(commands=['gerichte'])
        def send_meal(message):
            self.log.debug(f"[{message.chat.username}] Received message: {message.text}")
            keyboard = InlineKeyboardMarkup(row_width=3)
            buttons = [InlineButton(f"{i}", callback_data=f'gerichte_{i}') for i in range(1, 7)]
            keyboard.row(*buttons)
            response = "Wie viele Gerichte möchtest du?"
            self.bot.send_message(chat_id=message.chat.id, text=response, reply_markup=keyboard)

        @self.bot.message_handler(commands=['woechentlich'])
        def send_meal(message):
            self.log.debug(f"[{message.chat.username}] Received message: {message.text}")
            keyboard = InlineKeyboardMarkup()
            buttons = [InlineButton(f"{i}", callback_data=f'woechentlich_{i}') for i in range(0, 7)]
            keyboard.row(*buttons)
            response = "📅 Wie viele Gerichte möchtest du wöchentlich (Montags) erhalten?"
            self.bot.send_message(chat_id=message.chat.id, text=response, reply_markup=keyboard)


class TeleBotWrapper:
    log = create_logger("Telegram Messages")
    last_message_file = "data/messages.json"

    def __init__(self):
        self.bot = telebot.TeleBot(getenv('TELEGRAM_BOT_TOKEN'))
        self.messages = {}

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        message = self.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
        self.log.debug(f"Sending [{chat_id} | {message.id}]: {text}")
        self.save_last_message(chat_id, message.id)
        return message

    def send_document(self, chat_id, document, reply_markup=None, caption=None):
        message = self.bot.send_document(
            chat_id=chat_id, document=document, caption=caption, reply_markup=reply_markup
        )
        self.log.debug(f"Sending [{chat_id} | {message.id}]: {caption}")
        self.save_last_message(chat_id, message.id)
        return message

    def delete_message(self, chat_id, message_id=None):
        if message_id is None:
            self.delete_last_message(chat_id)
        else:
            self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            self.log.debug(f"Deleting [{chat_id} | {message_id}]")

    def delete_messages(self, chat_id, message_ids):
        for message_id in message_ids:
            self.delete_message(chat_id, message_id)

    def save_last_message(self, chat_id, message_id):
        chat_id = str(chat_id)
        message_queue = self.messages.get(chat_id, [])
        message_queue.append(message_id)
        self.messages[chat_id] = message_queue

    def delete_last_message(self, chat_id):
        chat_id = str(chat_id)
        message_queue = self.messages.get(chat_id, [])
        if message_queue is None:
            self.log.warning(f"Could not delete last message for chat {chat_id}")
            return
        last_message_id = message_queue.pop()
        self.bot.delete_message(chat_id=chat_id, message_id=last_message_id)
        self.log.debug(f"Deleting [{chat_id} | {last_message_id}]")
        self.messages[chat_id] = message_queue













if __name__ == "__main__":
    TelegramBot().start_bot(
        debug=False
    )