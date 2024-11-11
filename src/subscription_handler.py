import json
import schedule
import time
from utils.logger import create_logger


class SubscriptionHandler:
    log = create_logger("Subscription Handler")
    subscriptions_path = 'data/subscriptions.json'

    def __init__(self, bot, message_handler):
        self.bot = bot
        self.message_handler = message_handler

    def schedule_weekly_subscription_messages(self):
        schedule.every().monday.at("12:00").do(self.send_subscription_messages)
        while True:
            schedule.run_pending()
            time.sleep(60)

    def send_subscription_messages(self):
        self.log.info("Sending weekly meal plans!")
        with open(self.subscriptions_path, 'r') as file:
            subscriptions = json.load(file)
        for chat_id, num_meals in subscriptions.items():
            self.message_handler.send_meals_message(chat_id, num_meals, self.bot)

    def handle_subscription_callback(self, call):
        num_meals = int(call.data.replace('woechentlich_', ''))
        response = f"📅 Du hast dich für {num_meals} Gerichte pro Woche angemeldet!"
        self.bot.send_message(chat_id=call.message.chat.id, text=response)
        self.log.info(f"Subscribing {call.message.chat.id} to {num_meals} meals per week!")
        self.set_user_subscription(call.message.chat.id, num_meals)

    def set_user_subscription(self, chat_id, num_meals):
        with open(self.subscriptions_path, 'r') as file:
            subscriptions = json.load(file)
        subscriptions[str(chat_id)] = num_meals
        if num_meals == 0:
            del subscriptions[str(chat_id)]
        with open(self.subscriptions_path, 'w') as file:
            json.dump(subscriptions, file)