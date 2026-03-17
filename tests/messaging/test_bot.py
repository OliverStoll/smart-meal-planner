from messaging.bot import TelegramBot


def test_telegram_bot():
    handler = TelegramBot()
    handler.start_bot()
