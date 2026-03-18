from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton

from messaging.database.nosql import set_user_setting
from messaging.recipes import num_filtered_recipes
from settings import NOSQL_USER_DATA_REF
from database.nosql import nosql_client
from messaging.utils import str_to_int
from src.messaging.callbacks.settings_types import UserSettings
from messaging import CALLBACK_DELIM, MESSAGE_SETTING_CONFIGS


def get_user_settings(chat_id: int) -> UserSettings:
    ref = f"{NOSQL_USER_DATA_REF}/{chat_id}"
    user_settings_raw = nosql_client().get(ref=ref)
    if not user_settings_raw:
        return UserSettings()
    user_settings_data = {}
    for setting_name, setting_data in MESSAGE_SETTING_CONFIGS.items():
        setting_value = user_settings_raw.get(setting_name, {}).get("value", setting_data.default_value)
        setting_value = str_to_int(setting_value)
        user_settings_data[setting_name] = setting_value
    user_settings = UserSettings(**user_settings_data)
    return user_settings


def setting_value_confirmation_message(setting_name: str, value: str | int):
    setting_properties = MESSAGE_SETTING_CONFIGS.get(setting_name, None)
    if setting_properties.option_labels and value in setting_properties.option_labels:
        value = setting_properties.option_labels[value]
    response = setting_properties.confirmation_message.format(value=value)
    return response


def handle_setting_user_setting_option(name: str, value: str, chat_id: int) -> tuple[str, str | int]:
    """
    Handles the callback of the user setting selection. Sets the user setting and get the Setting Type object.

    Args:
        call_data (str): The data from the callback query.
        chat_id (int): The chat ID of the user.

    Returns:
        tuple[str, str | int]: The setting name and the selected option value.
    """
    # chat_id = message.chat.id
    value = str_to_int(value)
    set_user_setting(chat_id=chat_id, setting_name=name, setting_option=value)

    return name, value


def get_setting_options_menu(setting_name: str) -> tuple:
    setting_data = MESSAGE_SETTING_CONFIGS.get(setting_name, None)
    if not setting_data:
        return None, None
    keyboard = InlineKeyboardMarkup()
    keyboard_buttons = []
    for setting_option in setting_data.options:
        button = InlineButton(
            text=str(setting_option).capitalize(),
            callback_data=f"option{CALLBACK_DELIM}{setting_name}{CALLBACK_DELIM}{setting_option}",
        )
        keyboard_buttons.append(button)
    keyboard.row(*keyboard_buttons)

    return setting_data.query_message, keyboard


def recipe_filter_confirmation_message(chat_id: int) -> str:
    user_settings = get_user_settings(chat_id=chat_id)
    num_options = num_filtered_recipes(user_settings=user_settings)
    message = f"Es gibt insgesamt {num_options} passende Gerichte für deine Einstellungen."
    return message
