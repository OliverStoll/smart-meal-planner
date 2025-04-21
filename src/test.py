import telebot
from telebot import types

from dotenv import load_dotenv
import os
load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(token=token)
pdf_path='../data/temp_pdfs/1/11-Meter-Burger mit deftigem Hackfleisch.pdf'
thumb_path='../data/temp_thumbs/Untitled.png'
pdf_file = 'https://www.dkfz.de/fileadmin/user_upload/Krebspraevention/Download/pdf/Buecher_und_Berichte/2022_Alkoholatlas-Deutschland-2022_Auf-einen-Blick.pdf'


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Sends a welcome message when the bot is started.

    Parameters:
    - message: telebot.types.Message instance
    """
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("Get PDF", callback_data="get_pdf"),
        types.InlineKeyboardButton("Get Thumbnail", callback_data="get_thumb")
    )


    # Send document with thumbnail
    with open(pdf_path, 'rb') as pdf_file:
        with open(thumb_path, 'rb') as thumb_file:
            bot.send_document(
                message.chat.id,
                document=pdf_file,
                thumbnail=thumb_file,
                caption="Here is your PDF file 📄",
                reply_markup=markup
            )







if __name__ == '__main__':
    # Start the bot

    bot.polling(none_stop=True)
