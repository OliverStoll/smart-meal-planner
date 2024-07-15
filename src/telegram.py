import telebot
from os import getenv
from dotenv import load_dotenv

from utils.logger import create_logger

from meal_manager import HF_Meal_Manager

load_dotenv()
manager = HF_Meal_Manager()
bot = telebot.TeleBot(getenv('TELEGRAM_BOT_TOKEN'))
log = create_logger("Telegram Meal Bot")


def start_bot():
    while True:
        log.info("Starting Bot!")
        try:
            bot.polling()
        except Exception as e:
            log.error(f"Error while running the Bot: {e}")


@bot.message_handler(commands=['start', 'help'])
def send_intro(message):
    log.debug(f"Received message: {message.text}")
    response = (f"Hi! Um eine Einkaufsliste und die Rezepte für mehrere Gerichte zu erhalten,"
                f"schreib /gericht <Anzahl Gerichte>")
    bot.send_message(chat_id=message.chat.id, text=response)


@bot.message_handler(commands=['gericht', 'Gericht'])
def send_meal(message):
    command = message.text.split(" ")
    if len(command) != 2:
        response = "Bitte gib eine Zahl an, z.B. /gericht 3"
        bot.send_message(chat_id=message.chat.id, text=response)
        return
    try:
        num_meals = int(command[1])
    except ValueError:
        response = "Bitte gib eine Zahl an, z.B. /gericht 3"
        bot.send_message(chat_id=message.chat.id, text=response)
        return

    groceries_response, pdf_paths = manager.get_recipes(num_meals)
    # send meal as code block
    response = f"```  {groceries_response}```"
    log.info(f"Sending meal: {groceries_response}")
    bot.send_message(chat_id=message.chat.id, text=response, parse_mode='Markdown')
    for pdf in pdf_paths:
        with open(pdf, 'rb') as file:
            bot.send_document(chat_id=message.chat.id, document=file)


if __name__ == "__main__":
    # get_all_meals()
    start_bot()
