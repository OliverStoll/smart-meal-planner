import os
import pytest
from telebot import TeleBot

from messaging import CALLBACK_DELIM
from messaging.bot import (
    TelegramBot,
    INTRO_RESPONSE,
    SETTINGS_RESPONSE,
    MEALS_RESPONSE,
    WEEKLY_RESPONSE,
    FAVORITE_RESPONSE,
)

from unittest.mock import Mock, ANY

TEST_CHAT_ID = 123456789


@pytest.fixture
def recipe_id(cleaned_recipes) -> str:
    return cleaned_recipes.iloc[0]["id"]


@pytest.fixture(autouse=True)
def set_bot_env():
    os.environ["TELEGRAM_BOT_TOKEN"] = os.getenv("TEST_TELEGRAM_BOT_TOKEN")


class MockBot:
    def __init__(self):
        self.send_message = Mock()
        self.edit_message_text = Mock()
        self.answer_callback_query = Mock()
        self.delete_message = Mock()


class MockChat:
    def __init__(self, chat_id=TEST_CHAT_ID, username="testuser"):
        self.id = chat_id
        self.username = username


class MockMessage:
    def __init__(self, text="/start", chat_id=TEST_CHAT_ID, message_id=1):
        self.chat = MockChat(chat_id)
        self.message_id = message_id
        self.text = text


class MockCallback:
    """Mock object for callback queries"""

    def __init__(self, data, chat_id=TEST_CHAT_ID, message_id=1, callback_id="abc123"):
        self.data = data
        self.id = callback_id
        self.message = MockMessage(chat_id=chat_id, message_id=message_id)


def mock_message(text: str) -> Mock:
    message = Mock()
    message.chat.id = TEST_CHAT_ID
    message.chat.username = "testuser"
    message.text = text
    return message


def mock_callback(data: list[str]) -> MockCallback:
    data = CALLBACK_DELIM.join(data)
    callback = MockCallback(data=data)
    return callback


def get_message_handler(bot: TeleBot, command: str):
    for handler_data in bot.message_handlers:
        if command in handler_data["filters"]["commands"]:
            return handler_data["function"]
    raise Exception("Message Handler not found")


def get_callback_handler(bot, callback):
    for handler_data in bot.callback_query_handlers:
        if handler_data["filters"]["func"](callback):
            return handler_data["function"]
    raise Exception("Callback Handler not found")


def test_message_bot_instance_definitions():
    bot_instance = TelegramBot()
    bot_instance.setup_message_handlers()


def test_callback_definitions():
    bot_instance = TelegramBot()
    bot_instance.setup_message_callbacks()


def test_start_bot(monkeypatch):
    bot_instance = TelegramBot()
    monkeypatch.setattr(
        bot_instance.bot,
        "polling",
        lambda: (_ for _ in ()).throw(Exception("polling failed")),
    )
    with pytest.raises(Exception, match="polling failed"):
        bot_instance.start_bot()


def test_start_bot_persistant(monkeypatch):
    bot_instance = TelegramBot()
    monkeypatch.setattr(
        bot_instance.bot,
        "polling",
        lambda: (_ for _ in ()).throw(Exception("polling failed")),
    )
    with pytest.raises(Exception, match="polling failed"):
        bot_instance.start_bot_persistent()


class TestTelegramBotMessages:
    def handle_message_with_bot(self, command: str):
        instance = TelegramBot()
        handler_fn = get_message_handler(bot=instance.bot, command=command)
        instance.bot = Mock()
        message = mock_message("/" + command)
        handler_fn(message)
        return instance.bot

    def test_send_intro(self):
        bot = self.handle_message_with_bot("start")
        bot.send_message.assert_called_once_with(chat_id=TEST_CHAT_ID, text=INTRO_RESPONSE, parse_mode="Markdown")

    def test_change_options(self):
        bot = self.handle_message_with_bot("optionen")
        bot.send_message.assert_called_once_with(chat_id=TEST_CHAT_ID, text=SETTINGS_RESPONSE, reply_markup=ANY)
        _, kwargs = bot.send_message.call_args
        assert kwargs["reply_markup"] is not None

    def test_send_meal(self):
        bot = self.handle_message_with_bot("gerichte")
        bot.send_message.assert_called_once_with(chat_id=TEST_CHAT_ID, text=MEALS_RESPONSE, reply_markup=ANY)
        _, kwargs = bot.send_message.call_args
        assert kwargs["reply_markup"] is not None

    def test_send_weekly(self):
        bot = self.handle_message_with_bot("woechentlich")
        bot.send_message.assert_called_once_with(chat_id=TEST_CHAT_ID, text=WEEKLY_RESPONSE, reply_markup=ANY)
        _, kwargs = bot.send_message.call_args
        assert kwargs["reply_markup"] is not None

    def test_send_favorites(self):
        bot = self.handle_message_with_bot("favoriten")
        bot.send_message.assert_called_once_with(chat_id=TEST_CHAT_ID, text=FAVORITE_RESPONSE, reply_markup=ANY)
        _, kwargs = bot.send_message.call_args
        assert kwargs["reply_markup"] is not None


class TestTelegramBotCallbacks:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, cleaned_recipes):
        monkeypatch.setattr("messaging.bot.recipes_from_sql", lambda *_: cleaned_recipes)
        monkeypatch.setattr("messaging.recipes.recipes_from_sql", lambda *_: cleaned_recipes)
        monkeypatch.setattr("messaging.utils.recipes_from_sql", lambda *_: cleaned_recipes)

    def handles_callback_with_bot(self, data: list[str]):
        instance = TelegramBot()
        callback = mock_callback(data)
        handler_fn = get_callback_handler(bot=instance.bot, callback=callback)
        instance.bot = Mock()
        handler_fn(call=callback)
        return instance.bot

    def test_handle_settings_menu(self):
        bot = self.handles_callback_with_bot(data=["settings", "portions"])
        bot.edit_message_text.assert_called_once_with(chat_id=TEST_CHAT_ID, message_id=1, text=ANY, reply_markup=ANY)

    def test_handle_setting_value_set(self):
        bot = self.handles_callback_with_bot(data=["option", "portions", "3"])
        bot.edit_message_text.assert_called_once_with(
            chat_id=TEST_CHAT_ID,
            message_id=1,
            text="🍽️ Du erhältst jetzt Rezepte für 3 Portionen.",
        )

    def test_handle_setting_value_invalid(self):
        self.handles_callback_with_bot(data=["option", "portions"])

    def test_handle_weekly(self):
        bot = self.handles_callback_with_bot(data=["woechentlich", "1"])
        bot.send_message.assert_called_once_with(
            chat_id=TEST_CHAT_ID,
            text="📅 Du hast dich für 1 Gerichte pro Woche angemeldet!",
        )

    def test_handle_replace(self, recipe_id):
        bot = self.handles_callback_with_bot(data=["replace", "1", recipe_id])
        print(bot)  # TODO
        # TODO
        # bot.send_message.assert_called_once_with()
        # bot.edit_message_text.assert_called_once_with()

    def test_handle_favorize(self, recipe_id):
        bot = self.handles_callback_with_bot(data=["favorite", recipe_id])
        print(bot)  # TODO

    def test_handle_unfavorize(self, recipe_id):
        bot = self.handles_callback_with_bot(data=["unfavorite", recipe_id])
        print(bot)  # TODO

    def test_handle_meals(self):
        bot = self.handles_callback_with_bot(data=["gerichte", "2"])
        print(bot)  # TODO

    def test_handle_favorite_meals(self, recipe_id, monkeypatch):
        monkeypatch.setattr(
            "messaging.messaging.send_shopping_list_message",
            lambda **kwargs: MockMessage(message_id=3),
        )
        monkeypatch.setattr("messaging.bot.get_favorite_ids", lambda **kwargs: [recipe_id])
        bot = self.handles_callback_with_bot(data=["fav_gerichte", "2"])
        print(bot)  # TODO

    def test_invalid(self):
        bot = self.handles_callback_with_bot(data=["invalid-callback"])
        print(bot)  # TODO
