import json
import schedule
import time

from common_utils.logger import create_logger
from common_utils.apis.firebase import FirebaseClient
from common_utils.config import secret


class SubscriptionHandler:
    log = create_logger("Subscription Handler")
    subscriptions_path = 'data/subscriptions.json'
    subscriptions_ref = 'AppData/Telegram%20Meal%20Bot/Subscriptions'

    def __init__(self, bot, message_handler, firebase_secret_env='FIREBASE_REALTIME_DB_URL'):
        self.bot = bot
        self.message_handler = message_handler
        self.firebase_client = FirebaseClient(secret(firebase_secret_env))

    def send_subscription_messages(self):
        self.log.info("Sending weekly meal plans!")
        subscriptions = self.firebase_client.get_entry(self.subscriptions_ref)
        for chat_id, subscription_obj in subscriptions.items():
            num_meals = subscription_obj.get('num_meals', 0)
            self.message_handler.send_meals_message(
                chat_id=chat_id,
                num_meals=num_meals
            )

    def handle_subscription_callback(self, call):
        num_meals = int(call.data.replace('woechentlich_', ''))
        response = f"📅 Du hast dich für {num_meals} Gerichte pro Woche angemeldet!"
        self.bot.send_message(chat_id=call.message.chat.id, text=response)
        self.log.info(f"Subscribing {call.message.chat.id} to {num_meals} meals per week!")
        self.set_user_subscription(call.message.chat.id, num_meals)

    def set_user_subscription(self, chat_id, num_meals):
        self.log.info(f"Setting subscription for {chat_id} to {num_meals} meals.")
        ref = f'{self.subscriptions_ref}/{chat_id}'
        self.firebase_client.set_entry(
            ref=ref,
            data={
                'num_meals': num_meals
            }
        )