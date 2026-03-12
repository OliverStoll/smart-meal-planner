from schedule import every

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

    def schedule_weekly_meal_plans(self, time="10:00"):
        """
        Schedule the weekly meal plans to be sent every Sunday at 10:00 AM.
        """
        every().monday.at(time).do(self.send_subscription_messages)
        self.log.info("Weekly meal plans scheduled for Mondays at 10:00 AM.")


    def send_subscription_messages(self):
        self.log.info("Sending weekly meal plans!")
        subscriptions = self.get_all_subscriptions()
        for chat_id, num_meals in subscriptions.items():
            self.message_handler.send_full_recipes_message(
                chat_id=chat_id,
                num_meals=num_meals
            )

    def handle_subscription_callback(self, call):
        num_meals = int(call.data.replace('woechentlich|', ''))
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

    def get_all_subscriptions(self):
        """
        Get all active subscriptions from the Firebase database.

        Returns:
            A dictionary containing all active subscriptions, with chat IDs as keys and number of meals as values.
        """

        self.log.info("Getting all subscriptions.")
        subscriptions_data = self.firebase_client.get_entry(self.subscriptions_ref)
        if not subscriptions_data:
            return {}

        subscription = {
            int(chat_id): subscription_obj.get('num_meals', 0)
            for chat_id, subscription_obj in subscriptions_data.items() if subscription_obj.get('num_meals', 0) > 0
        }

        return subscription

    def get_user_subscription(self, chat_id: int) -> int:
        """
        Get the number of meals the user is subscribed to, if any.

        Args:
            chat_id: The chat ID of the user.

        Returns:
            Number of meals the user is subscribed to. If no subscription exists, return 0.
        """
        self.log.info(f"Getting subscription for {chat_id}.")
        ref = f'{self.subscriptions_ref}/{chat_id}'
        subscription = self.firebase_client.get_entry(ref)
        if not subscription:
            return 0

        return subscription.get('num_meals', 0)
