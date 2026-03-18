from messaging.callbacks.subscriptions import get_all_subscriptions, SubscriptionHandler


def test_get_all_subscriptions():
    subscription = get_all_subscriptions()
    print(subscription)


def test_send_subscription_messages(monkeypatch):
    monkeypatch.setattr(
        "messaging.callbacks.subscriptions.get_all_subscriptions",
        lambda *args: {12345: 3},
    )
    handler = SubscriptionHandler(bot=None)
    handler.send_subscription_messages()
