from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from messaging import CALLBACK_DELIM
from messaging.utils import callback_str


def favorize_button(recipe_id: int, is_favorite: bool):
    fav_callback = callback_str(["favorite", recipe_id]) if not is_favorite else callback_str(["unfavorite", recipe_id])
    return InlineKeyboardButton(
        text="⭐️ Speichern" if not is_favorite else "❌ Unfavorisieren",
        callback_data=fav_callback,
    )


def replace_button(recipe_id: int, shopping_list_msg_id: int):
    return InlineKeyboardButton(
        text="🔄 Austauschen",
        callback_data=callback_str(["replace", shopping_list_msg_id, recipe_id]),
    )


def create_settings_keyboard() -> InlineKeyboardMarkup:
    settings_keyboard = InlineKeyboardMarkup()
    settings_keyboard.row(
        InlineKeyboardButton("🍽️ Portionsanzahl", callback_data="settings|portions"),
        InlineKeyboardButton("🥦 Ernährungsform", callback_data="settings|meal_type"),
    )
    settings_keyboard.row(
        InlineKeyboardButton("⏱️ Kochzeit", callback_data="settings|max_duration"),
        InlineKeyboardButton("🔥 Kalorien (min.)", callback_data="settings|cal_min"),
    )
    return settings_keyboard


def enumerated_keyboard(callback_prefix, start_idx, end_idx):
    """Create a keyboard with enumerated buttons."""
    keyboard = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton(f"{i}", callback_data=f"{callback_prefix}{CALLBACK_DELIM}{i}")
        for i in range(start_idx, end_idx + 1)
    ]
    keyboard.row(*buttons)
    return keyboard
