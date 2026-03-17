from messaging.callbacks.subscriptions import get_all_subscriptions, SubscriptionHandler


def test_get_all_subscriptions():
    subscription = get_all_subscriptions()
    print(subscription)


def test_send_subscription_messages():
    handler = SubscriptionHandler(bot=None)
    handler.send_subscription_messages()
