import telebot
import random
import pandas as pd
from os import getenv
from dotenv import load_dotenv

from utils.logger import create_logger
from utils.config import load_config_yaml, get_root_dir

from meal_manager import HF_Meal_Manager

load_dotenv()
manager = HF_Meal_Manager()
bot = telebot.TeleBot(getenv('TELEGRAM_BOT_TOKEN'))
log = create_logger("Telegram Meal Bot")


def start_bot():
    log.info("Bot is running!")
    try:
        bot.polling()
    except Exception as e:
        log.error(f"Error while running the Bot: {e}")
        raise e


@bot.message_handler(commands=['start', 'help'])
def send_intro(message):
    log.debug(f"Received message: {message.text}")
    response = (f"Hi! Um eine Einkaufsliste und die Rezepte für mehrere Gerichte zu erhalten,"
                f"schreib /gericht <Anzahl Gerichte>")
    bot.send_message(chat_id=message.chat.id, text=response)


@bot.message_handler(commands=['gericht'])
def send_meal(message):
    command = message.text.split(" ")

    try:
        num_meals = int(command[1])
    except ValueError:
        response = "Bitte gib eine Zahl an, z.B. /gericht 3"
        bot.send_message(chat_id=message.chat.id, text=response)
        return

    groceries, pdf_paths = manager.get_recipes(num_meals)
    response = f"**Einkaufsliste für {num_meals} Gerichte:**\n{groceries}"
    log.info(f"Sending meal: {response}")
    bot.send_message(chat_id=message.chat.id, text=response, parse_mode='Markdown')
    for pdf in pdf_paths:
        with open(pdf, 'rb') as file:
            bot.send_document(chat_id=message.chat.id, document=file)


if __name__ == "__main__":
    # get_all_meals()
    start_bot()
