
from common_utils.logger import create_logger
from common_utils.apis.firebase import FirebaseClient
from common_utils.config import secret


class SubscriptionMealSender:
    log = create_logger("Subscription Meal Sender")

    def __init__(self, firebase_env='FIREBASE_REALTIME_DB_URL'):
        firebase_handler = FirebaseClient(secret(firebase_env))

    def send_subscription_messages(self):
        self.log.info("Sending weekly meal plans!")
        subscriptions = self.get_subscriptions()

    def get_subscriptions(self):
