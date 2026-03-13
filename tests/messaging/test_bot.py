import pytest
from unittest.mock import MagicMock, patch

from messaging.bot import TelegramBot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_fake_message_handler():
    """Return (registry_dict, side_effect_fn) for capturing message handlers."""
    registry = {}

    def side_effect(**kwargs):
        def decorator(fn):
            for cmd in kwargs.get("commands", []):
                registry[cmd] = fn
            return fn
        return decorator

    return registry, side_effect


def _make_fake_callback_handler():
    """Return (registry_list, side_effect_fn) for capturing callback handlers."""
    registry = []

    def side_effect(func=None, **kwargs):
        filter_fn = func

        def decorator(handler_fn):
            registry.append((filter_fn, handler_fn))
            return handler_fn

        return decorator

    return registry, side_effect


@pytest.fixture
def mock_bot_instance():
    return MagicMock()


@pytest.fixture
def telegram_bot(mock_bot_instance):
    msg_registry, fake_msg_handler = _make_fake_message_handler()
    cb_registry, fake_cb_handler = _make_fake_callback_handler()

    mock_bot_instance.message_handler.side_effect = fake_msg_handler
    mock_bot_instance.callback_query_handler.side_effect = fake_cb_handler

    with patch("messaging.bot.telebot.TeleBot", return_value=mock_bot_instance), \
         patch("messaging.bot.load_dotenv"), \
         patch("messaging.bot.getenv", return_value="fake-token"), \
         patch("messaging.bot.RecipeManager"), \
         patch("messaging.bot.MessageHandler"), \
         patch("messaging.bot.SubscriptionHandler"), \
         patch("messaging.bot.SettingsHandler"), \
         patch("messaging.bot.FavoritesHandler"):
        bot = TelegramBot()

    return bot, mock_bot_instance, msg_registry, cb_registry


def _make_message(chat_id=123, username="testuser", text="/start"):
    msg = MagicMock()
    msg.chat.id = chat_id
    msg.chat.username = username
    msg.text = text
    return msg


def _make_call(data="settings|portions", chat_id=123, message_id=10, username="testuser"):
    call = MagicMock()
    call.data = data
    call.message.chat.id = chat_id
    call.message.chat.username = username
    call.message.message_id = message_id
    return call


# ---------------------------------------------------------------------------
# TelegramBot.__init__ / setup
# ---------------------------------------------------------------------------

class TestTelegramBotInit:
    def test_message_handlers_registered(self, telegram_bot):
        _, _, msg_registry, _ = telegram_bot
        assert len(msg_registry) > 0

    def test_callback_handlers_registered(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        assert len(cb_registry) > 0

    def test_expected_commands_registered(self, telegram_bot):
        _, _, msg_registry, _ = telegram_bot
        for cmd in ("start", "help", "gerichte", "woechentlich", "favoriten"):
            assert cmd in msg_registry, f"Expected command '{cmd}' to be registered"

    def test_settings_commands_registered(self, telegram_bot):
        _, _, msg_registry, _ = telegram_bot
        # At least one settings-related command should be registered
        settings_cmds = {"optionen", "options", "einstellungen", "settings"}
        assert settings_cmds & set(msg_registry.keys())

    def test_callback_delimiter_set(self, telegram_bot):
        bot, _, _, _ = telegram_bot
        assert bot.callback_delimiter == "|"

    def test_settings_keyboard_has_rows(self, telegram_bot):
        bot, _, _, _ = telegram_bot
        # The class-level settings_keyboard has inline buttons
        assert len(TelegramBot.settings_keyboard.keyboard) > 0


# ---------------------------------------------------------------------------
# TelegramBot._start_bot_once
# ---------------------------------------------------------------------------

class TestStartBotOnce:
    def test_calls_polling(self, telegram_bot):
        bot, mock_bot_instance, _, _ = telegram_bot
        bot._start_bot_once(raise_exceptions=False)
        mock_bot_instance.polling.assert_called_once()

    def test_suppresses_exception_when_flag_false(self, telegram_bot):
        bot, mock_bot_instance, _, _ = telegram_bot
        mock_bot_instance.polling.side_effect = ConnectionError("network error")
        # Should NOT raise
        bot._start_bot_once(raise_exceptions=False)

    def test_reraises_exception_when_flag_true(self, telegram_bot):
        bot, mock_bot_instance, _, _ = telegram_bot
        mock_bot_instance.polling.side_effect = RuntimeError("fatal")
        with pytest.raises(RuntimeError):
            bot._start_bot_once(raise_exceptions=True)

    def test_reraises_original_exception_type(self, telegram_bot):
        bot, mock_bot_instance, _, _ = telegram_bot
        mock_bot_instance.polling.side_effect = ValueError("bad value")
        with pytest.raises(ValueError):
            bot._start_bot_once(raise_exceptions=True)


# ---------------------------------------------------------------------------
# Message handler: /start and /help
# ---------------------------------------------------------------------------

class TestStartHelpHandler:
    def test_sends_intro_message(self, telegram_bot):
        bot, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(text="/start")
        msg_registry["start"](message)
        mock_bot_instance.send_message.assert_called_once()

    def test_intro_message_sent_to_correct_chat(self, telegram_bot):
        _, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(chat_id=456, text="/start")
        msg_registry["start"](message)
        call_kwargs = mock_bot_instance.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 456

    def test_help_handler_shares_intro_text(self, telegram_bot):
        _, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(text="/help")
        msg_registry["help"](message)
        mock_bot_instance.send_message.assert_called_once()


# ---------------------------------------------------------------------------
# Message handler: /einstellungen (settings)
# ---------------------------------------------------------------------------

class TestSettingsHandler:
    def test_sends_message_with_keyboard(self, telegram_bot):
        _, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(text="/einstellungen")
        msg_registry["einstellungen"](message)
        call_kwargs = mock_bot_instance.send_message.call_args.kwargs
        assert "reply_markup" in call_kwargs

    def test_sends_message_to_correct_chat(self, telegram_bot):
        _, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(chat_id=789, text="/einstellungen")
        msg_registry["einstellungen"](message)
        call_kwargs = mock_bot_instance.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 789


# ---------------------------------------------------------------------------
# Message handler: /gerichte
# ---------------------------------------------------------------------------

class TestGerichteHandler:
    def test_sends_message_with_keyboard(self, telegram_bot):
        _, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(text="/gerichte")
        msg_registry["gerichte"](message)
        call_kwargs = mock_bot_instance.send_message.call_args.kwargs
        assert "reply_markup" in call_kwargs

    def test_sends_message_to_correct_chat(self, telegram_bot):
        _, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(chat_id=101, text="/gerichte")
        msg_registry["gerichte"](message)
        call_kwargs = mock_bot_instance.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 101


# ---------------------------------------------------------------------------
# Message handler: /woechentlich
# ---------------------------------------------------------------------------

class TestWoechentlichHandler:
    def test_sends_message_with_keyboard(self, telegram_bot):
        _, mock_bot_instance, msg_registry, _ = telegram_bot
        message = _make_message(text="/woechentlich")
        msg_registry["woechentlich"](message)
        call_kwargs = mock_bot_instance.send_message.call_args.kwargs
        assert "reply_markup" in call_kwargs


# ---------------------------------------------------------------------------
# Message handler: /favoriten
# ---------------------------------------------------------------------------

class TestFavoritenHandler:
    def test_sends_message(self, telegram_bot):
        bot, mock_bot_instance, msg_registry, _ = telegram_bot
        # favorites_handler.get_favorites returns a list
        bot.favorites_handler.get_favorites.return_value = ["r1", "r2", "r3"]
        message = _make_message(text="/favoriten")
        msg_registry["favoriten"](message)
        mock_bot_instance.send_message.assert_called_once()

    def test_no_favorites_sends_empty_keyboard(self, telegram_bot):
        bot, mock_bot_instance, msg_registry, _ = telegram_bot
        bot.favorites_handler.get_favorites.return_value = []
        message = _make_message(text="/favoriten")
        msg_registry["favoriten"](message)
        mock_bot_instance.send_message.assert_called_once()


# ---------------------------------------------------------------------------
# Callback: settings| prefix
# ---------------------------------------------------------------------------

class TestSettingsCallbackHandler:
    def _get_handler(self, cb_registry, prefix="settings|"):
        for filter_fn, handler_fn in cb_registry:
            call = _make_call(data=prefix)
            if filter_fn and filter_fn(call):
                return handler_fn
        return None

    def test_settings_handler_found(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry, "settings|portions")
        assert handler is not None

    def test_valid_setting_edits_message(self, telegram_bot):
        bot, mock_bot_instance, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry, "settings|portions")
        bot.settings.get_setting_options_menu.return_value = {
            "text": "Choose portions:", "reply_markup": MagicMock()
        }
        call = _make_call(data="settings|portions")
        handler(call)
        mock_bot_instance.edit_message_text.assert_called_once()

    def test_invalid_setting_does_not_edit_message(self, telegram_bot):
        bot, mock_bot_instance, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry, "settings|portions")
        bot.settings.get_setting_options_menu.return_value = None
        call = _make_call(data="settings|nonexistent")
        handler(call)
        mock_bot_instance.edit_message_text.assert_not_called()


# ---------------------------------------------------------------------------
# Callback: woechentlich| prefix
# ---------------------------------------------------------------------------

class TestWoechentlichCallbackHandler:
    def _get_handler(self, cb_registry, prefix="woechentlich|"):
        for filter_fn, handler_fn in cb_registry:
            call = _make_call(data=prefix + "3")
            if filter_fn and filter_fn(call):
                return handler_fn
        return None

    def test_woechentlich_handler_found(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        assert handler is not None

    def test_delegates_to_subscription_handler(self, telegram_bot):
        bot, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        call = _make_call(data="woechentlich|3")
        handler(call)
        bot.subscriptions_handler.handle_subscription_callback.assert_called_once_with(call)


# ---------------------------------------------------------------------------
# Callback: gerichte| prefix
# ---------------------------------------------------------------------------

class TestGerichteCallbackHandler:
    def _get_handler(self, cb_registry, data="gerichte|3"):
        for filter_fn, handler_fn in cb_registry:
            call = _make_call(data=data)
            if filter_fn and filter_fn(call):
                return handler_fn
        return None

    def test_gerichte_callback_handler_found(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        assert handler is not None

    def test_calls_send_full_recipes_message(self, telegram_bot):
        bot, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        call = _make_call(data="gerichte|3")
        handler(call)
        bot.message_handler.send_full_recipes_message.assert_called_once()

    def test_invalid_gerichte_value_does_not_raise(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        call = _make_call(data="gerichte|not_a_number")
        # Should not raise
        handler(call)


# ---------------------------------------------------------------------------
# Callback: replace| prefix
# ---------------------------------------------------------------------------

class TestReplaceCallbackHandler:
    def _get_handler(self, cb_registry, data="replace|10|r1"):
        for filter_fn, handler_fn in cb_registry:
            call = _make_call(data=data)
            if filter_fn and filter_fn(call):
                return handler_fn
        return None

    def test_replace_handler_found(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        assert handler is not None

    def test_calls_resend_messages_to_replace_meal(self, telegram_bot):
        bot, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        call = _make_call(data="replace|10|r1")
        handler(call)
        bot.message_handler.resend_messages_to_replace_meal.assert_called_once()

    def test_invalid_replace_format_does_not_raise(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        call = _make_call(data="replace|only_two_parts")
        # Should not raise
        handler(call)


# ---------------------------------------------------------------------------
# Callback: favorite| prefix
# ---------------------------------------------------------------------------

class TestFavoriteCallbackHandler:
    def _get_handler(self, cb_registry, data="favorite|r1"):
        for filter_fn, handler_fn in cb_registry:
            call = _make_call(data=data)
            if filter_fn and filter_fn(call):
                return handler_fn
        return None

    def test_favorite_handler_found(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        assert handler is not None

    def test_calls_favorize_recipe(self, telegram_bot):
        bot, mock_bot_instance, _, cb_registry = telegram_bot
        bot.recipes.get_recipe_titles_by_id = MagicMock(return_value=["Pasta Primavera"])
        handler = self._get_handler(cb_registry)
        call = _make_call(data="favorite|r1")
        handler(call)
        bot.favorites_handler.favorize_recipe.assert_called_once()

    def test_answers_callback_query(self, telegram_bot):
        bot, mock_bot_instance, _, cb_registry = telegram_bot
        bot.recipes.get_recipe_titles_by_id = MagicMock(return_value=["Pasta Primavera"])
        handler = self._get_handler(cb_registry)
        call = _make_call(data="favorite|r1")
        handler(call)
        mock_bot_instance.answer_callback_query.assert_called_once()


# ---------------------------------------------------------------------------
# Callback: unfavorite| prefix
# ---------------------------------------------------------------------------

class TestUnfavoriteCallbackHandler:
    def _get_handler(self, cb_registry, data="unfavorite|r1"):
        for filter_fn, handler_fn in cb_registry:
            call = _make_call(data=data)
            if filter_fn and filter_fn(call):
                return handler_fn
        return None

    def test_unfavorite_handler_found(self, telegram_bot):
        _, _, _, cb_registry = telegram_bot
        handler = self._get_handler(cb_registry)
        assert handler is not None

    def test_calls_unfavorize_recipe(self, telegram_bot):
        bot, mock_bot_instance, _, cb_registry = telegram_bot
        bot.recipes.get_recipe_titles_by_id = MagicMock(return_value=["Pasta Primavera"])
        handler = self._get_handler(cb_registry)
        call = _make_call(data="unfavorite|r1")
        handler(call)
        bot.favorites_handler.unfavorize_recipe.assert_called_once()
