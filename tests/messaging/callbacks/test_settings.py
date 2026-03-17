import pytest
from unittest.mock import MagicMock, patch

from messaging.callbacks.settings import SettingsHandler


@pytest.fixture
def mock_firebase():
    return MagicMock()


@pytest.fixture
def settings_handler(mock_firebase):
    with patch(
        "messaging.callbacks.settings.FirebaseClient", return_value=mock_firebase
    ):
        handler = SettingsHandler()
    return handler


class TestTryConvertStrToInt:
    def test_converts_integer_string(self):
        assert SettingsHandler._try_convert_str_to_int("42") == 42

    def test_returns_string_unchanged_if_not_int(self):
        assert SettingsHandler._try_convert_str_to_int("vegan") == "vegan"

    def test_converts_negative_integer_string(self):
        assert SettingsHandler._try_convert_str_to_int("-5") == -5

    def test_leaves_float_string_unchanged(self):
        result = SettingsHandler._try_convert_str_to_int("3.14")
        assert result == "3.14"


class TestGetCompleteFilterConfirmationMessage:
    def test_message_contains_count(self):
        msg = SettingsHandler.get_complete_filter_confirmation_message(42)
        assert "42" in msg

    def test_returns_string(self):
        msg = SettingsHandler.get_complete_filter_confirmation_message(10)
        assert isinstance(msg, str)

    def test_message_with_zero(self):
        msg = SettingsHandler.get_complete_filter_confirmation_message(0)
        assert "0" in msg


class TestGetSettingOptionConfirmationMessage:
    def test_returns_confirmation_with_value_for_portions(self, settings_handler):
        msg = settings_handler.get_setting_option_confirmation_message("portions", 3)
        assert "3" in msg

    def test_returns_confirmation_with_label_for_meal_type(self, settings_handler):
        msg = settings_handler.get_setting_option_confirmation_message(
            "meal_type", "vegan"
        )
        assert "vegane" in msg

    def test_returns_confirmation_without_label_when_no_label_defined(
        self, settings_handler
    ):
        msg = settings_handler.get_setting_option_confirmation_message("portions", 4)
        assert "4" in msg

    def test_returns_string(self, settings_handler):
        msg = settings_handler.get_setting_option_confirmation_message("cal_min", 500)
        assert isinstance(msg, str)


class TestGetSettingProperties:
    def test_returns_existing_setting(self, settings_handler):
        props = settings_handler.get_setting_properties("portions")
        assert props is not None
        assert props.name == "portions"

    def test_returns_none_for_unknown_setting(self, settings_handler):
        props = settings_handler.get_setting_properties("unknown_setting")
        assert props is None

    def test_all_expected_settings_exist(self, settings_handler):
        for setting_name in ["portions", "meal_type", "max_duration", "cal_min"]:
            props = settings_handler.get_setting_properties(setting_name)
            assert props is not None, f"Setting '{setting_name}' should exist"


class TestGetSettingOptionsMenu:
    def test_returns_menu_for_valid_setting(self, settings_handler):
        result = settings_handler.get_setting_options_menu("portions")
        assert result is not None
        assert "text" in result
        assert "reply_markup" in result

    def test_returns_none_for_unknown_setting(self, settings_handler):
        result = settings_handler.get_setting_options_menu("nonexistent")
        assert result is None

    def test_menu_text_matches_query_message(self, settings_handler):
        result = settings_handler.get_setting_options_menu("portions")
        assert "Portionen" in result["text"]


class TestHandleSettingUserSettingOption:
    def test_parses_callback_data_correctly(self, settings_handler, mock_firebase):
        setting_name, option = settings_handler.handle_setting_user_setting_option(
            call_data="portions|3", chat_id=123
        )
        assert setting_name == "portions"
        assert option == 3

    def test_calls_set_user_setting(self, settings_handler, mock_firebase):
        settings_handler.handle_setting_user_setting_option(
            call_data="portions|2", chat_id=456
        )
        mock_firebase.set_entry.assert_called_once()

    def test_converts_option_to_int_when_possible(
        self, settings_handler, mock_firebase
    ):
        _, option = settings_handler.handle_setting_user_setting_option(
            call_data="max_duration|30", chat_id=789
        )
        assert option == 30
        assert isinstance(option, int)

    def test_keeps_string_option_as_string(self, settings_handler, mock_firebase):
        _, option = settings_handler.handle_setting_user_setting_option(
            call_data="meal_type|vegan", chat_id=101
        )
        assert option == "vegan"
        assert isinstance(option, str)


class TestGetUserSettings:
    def test_returns_default_settings_when_no_firebase_data(
        self, settings_handler, mock_firebase
    ):
        mock_firebase.get_entry.return_value = None
        result = settings_handler.get_user_settings(chat_id=123)
        assert result.portions == 2
        assert result.meal_type == "alle"
        assert result.max_duration == 120
        assert result.cal_min == 0

    def test_returns_stored_settings_from_firebase(
        self, settings_handler, mock_firebase
    ):
        mock_firebase.get_entry.return_value = {
            "portions": {"value": 4},
            "meal_type": {"value": "vegan"},
            "max_duration": {"value": 30},
            "cal_min": {"value": 500},
        }
        result = settings_handler.get_user_settings(chat_id=123)
        assert result.portions == 4
        assert result.meal_type == "vegan"
        assert result.max_duration == 30
        assert result.cal_min == 500

    def test_uses_default_for_missing_settings(self, settings_handler, mock_firebase):
        mock_firebase.get_entry.return_value = {
            "portions": {"value": 3},
        }
        result = settings_handler.get_user_settings(chat_id=123)
        assert result.portions == 3
        assert result.meal_type == "alle"
        assert result.max_duration == 120
