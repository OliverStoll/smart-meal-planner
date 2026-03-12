import pytest
from unittest.mock import MagicMock, patch

from messaging.callbacks.subscriptions import SubscriptionHandler


@pytest.fixture
def mock_bot():
    return MagicMock()


@pytest.fixture
def mock_message_handler():
    return MagicMock()


@pytest.fixture
def mock_firebase():
    return MagicMock()


@pytest.fixture
def subscription_handler(mock_bot, mock_message_handler, mock_firebase):
    with patch("messaging.callbacks.subscriptions.FirebaseClient", return_value=mock_firebase):
        handler = SubscriptionHandler(
            bot=mock_bot,
            message_handler=mock_message_handler,
        )
    return handler, mock_bot, mock_message_handler, mock_firebase


class TestGetAllSubscriptions:
    def test_returns_dict_with_subscriptions(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        mock_firebase.get_entry.return_value = {
            "111": {"num_meals": 3},
            "222": {"num_meals": 5},
        }
        result = handler.get_all_subscriptions()
        assert 111 in result
        assert 222 in result
        assert result[111] == 3
        assert result[222] == 5

    def test_returns_empty_dict_when_no_subscriptions(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        mock_firebase.get_entry.return_value = None
        result = handler.get_all_subscriptions()
        assert result == {}

    def test_excludes_subscriptions_with_zero_meals(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        mock_firebase.get_entry.return_value = {
            "111": {"num_meals": 0},
            "222": {"num_meals": 3},
        }
        result = handler.get_all_subscriptions()
        assert 111 not in result
        assert 222 in result


class TestGetUserSubscription:
    def test_returns_num_meals_for_subscribed_user(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        mock_firebase.get_entry.return_value = {"num_meals": 4}
        result = handler.get_user_subscription(chat_id=123)
        assert result == 4

    def test_returns_zero_when_no_subscription(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        mock_firebase.get_entry.return_value = None
        result = handler.get_user_subscription(chat_id=123)
        assert result == 0

    def test_returns_zero_when_num_meals_missing(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        mock_firebase.get_entry.return_value = {}
        result = handler.get_user_subscription(chat_id=123)
        assert result == 0


class TestSetUserSubscription:
    def test_calls_firebase_set_entry(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        handler.set_user_subscription(chat_id=123, num_meals=3)
        mock_firebase.set_entry.assert_called_once()

    def test_stores_correct_num_meals(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        handler.set_user_subscription(chat_id=456, num_meals=5)
        call_kwargs = mock_firebase.set_entry.call_args.kwargs
        assert call_kwargs["data"] == {"num_meals": 5}

    def test_uses_correct_ref_with_chat_id(self, subscription_handler):
        handler, _, _, mock_firebase = subscription_handler
        handler.set_user_subscription(chat_id=789, num_meals=2)
        call_kwargs = mock_firebase.set_entry.call_args.kwargs
        assert "789" in call_kwargs["ref"]


class TestHandleSubscriptionCallback:
    def test_sends_confirmation_message(self, subscription_handler):
        handler, mock_bot, _, mock_firebase = subscription_handler
        call = MagicMock()
        call.data = "woechentlich|4"
        call.message.chat.id = 123
        mock_firebase.set_entry.return_value = None
        handler.handle_subscription_callback(call)
        mock_bot.send_message.assert_called_once()

    def test_confirmation_message_contains_meal_count(self, subscription_handler):
        handler, mock_bot, _, mock_firebase = subscription_handler
        call = MagicMock()
        call.data = "woechentlich|3"
        call.message.chat.id = 456
        handler.handle_subscription_callback(call)
        mock_bot.send_message.assert_called_once()
        send_kwargs = mock_bot.send_message.call_args.kwargs
        send_args = mock_bot.send_message.call_args.args
        sent_text = send_kwargs.get("text") or (send_args[1] if len(send_args) > 1 else "")
        assert "3" in sent_text
