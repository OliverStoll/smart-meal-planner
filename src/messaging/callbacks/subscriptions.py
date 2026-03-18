from schedule import every
from logs.logs import create_logger

from settings import NOSQL_SUBSCRIPTION_REF
from database.nosql import nosql_client
from messaging.messaging import send_full_message

log = create_logger("Subscription Handler")


def subscription_num_meals(chat_id: int) -> int:
    """Get the number of meals the user is subscribed to, if any."""
    log.info(f"Getting subscription for {chat_id}.")
    ref = f"{NOSQL_SUBSCRIPTION_REF}/{chat_id}"
    subscription = nosql_client().get(ref)
    if not subscription:
        return 0
    return subscription.get("num_meals", 0)


def get_all_subscriptions() -> dict[int, int]:
    """
    Returns:
        A dictionary containing all active subscriptions, with chat IDs as keys and number of meals as values.
    """
    log.info("Getting all subscriptions.")
    subscriptions_data = nosql_client().get(NOSQL_SUBSCRIPTION_REF)
    if not subscriptions_data:
        return {}

    subscriptions = {}
    for chat_id, subscription_instance in subscriptions_data.items():
        num_meals = subscription_instance.get("num_meals", 0)
        if num_meals > 0:
            subscriptions[int(chat_id)] = num_meals
    return subscriptions


def set_user_subscription(chat_id, num_meals):
    log.info(f"Setting subscription for {chat_id} to {num_meals} meals.")
    ref = f"{NOSQL_SUBSCRIPTION_REF}/{chat_id}"
    nosql_client().set(ref=ref, data={"num_meals": num_meals})


class SubscriptionHandler:
    def __init__(self, bot):
        self.bot = bot

    def schedule_weekly_meal_plans(self, time="10:00"):
        """Schedule the weekly meal plans to be sent every Sunday at 10:00 AM."""
        every().monday.at(time).do(self.send_subscription_messages)
        log.info("Weekly meal plans scheduled for Mondays at 10:00 AM.")

    def send_subscription_messages(self):
        log.info("Sending weekly meal plans!")
        subscriptions = get_all_subscriptions()
        for chat_id, num_meals in subscriptions.items():
            send_full_message(bot=self.bot, chat_id=chat_id, num_meals=num_meals)
