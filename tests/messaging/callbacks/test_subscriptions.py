from unittest.mock import MagicMock

from messaging.callbacks.subscriptions import get_all_subscriptions, SubscriptionHandler


def test_get_all_subscriptions():
    subscription = get_all_subscriptions()
    print(subscription)


def test_send_subscription_messages(monkeypatch, cleaned_recipes):
    mock = MagicMock()
    monkeypatch.setattr(
        "messaging.callbacks.subscriptions.get_all_subscriptions",
        lambda *args: {12345: 3},
    )
    for module in ["messaging.messaging", "messaging.utils"]:
        monkeypatch.setattr(module + ".recipes_from_sql", lambda *args: cleaned_recipes)
    handler = SubscriptionHandler(bot=mock)
    handler.send_subscription_messages()
