import json
from dataclasses import dataclass
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from telebot import types, TeleBot

from common_utils.apis.firebase import FirebaseClient
from common_utils.config import secret

# from src.telegram.recipes import RecipeManager


@dataclass
class SettingsType:
    name: str
    friendly_name: str
    options: list[str | int]
    default_value: str | int
    query_message: str
    confirmation_message: str
    option_labels: dict[str, str] = None
    is_filter: bool = False
    

@dataclass
class UserSettings:
    portions: int = 2
    meal_type: str = 'alle'
    max_duration: int = 120
    cal_min: int = 0


class SettingsHandler:
    user_settings_path = 'data/options.json'
    user_settings_ref = 'AppData/Telegram Meal Bot/User Settings'
    firebase_env = 'FIREBASE_REALTIME_DB_URL'
    settings: dict[str, SettingsType] = {
        'portions': SettingsType(
            name='portions',
            friendly_name='Portionsanzahl',
            options=[1, 2, 3, 4, 5, 6],
            default_value=2,
            query_message='🍽️ Wähle die Anzahl der Portionen pro Gericht:',
            confirmation_message='🍽️ Du erhältst jetzt Rezepte für {value} Portionen.',
        ),
        'meal_type': SettingsType(
            name='meal_type',
            friendly_name='Art der Gerichte',
            options=['alle', 'vegetarisch', 'vegan', 'protein'],
            default_value='alle',
            query_message='🥗 Wähle die Art der Gerichte:',
            confirmation_message='🥗 Du erhältst jetzt {value} Gerichte.',
            option_labels={
                'alle': 'alle',
                'vegetarisch': 'vegetarische',
                'vegan': 'vegane',
                'protein': 'proteinreiche',
            },
            is_filter=True,
        ),
        'max_duration': SettingsType(
            name='max_duration',
            friendly_name='Kochzeit',
            options=[10, 15, 20, 25, 30, 45, 60, 90],
            default_value=120,
            query_message='⏱️ Wähle die maximale Kochzeit (in Minuten):',
            confirmation_message='⏱️ Deine maximale Kochzeit beträgt {value} Minuten.',
            is_filter=True,
        ),
        'cal_min': SettingsType(
            name='cal_min',
            friendly_name='Kalorien (min.)',
            options=[0, 500, 600, 700, 800, 900],
            default_value=0,
            query_message='🔥 Wähle die minimalen Kalorien pro Portion:',
            confirmation_message='🔥 Du erhältst jetzt Gerichte mit mindestens {value} kcal pro Portion.',
            is_filter=True,
        )
    }

    def __init__(
            self,
            bot: TeleBot,
            recipe_manager,  #  : RecipeManager,
            callback_delimiter: str,
            firebase_client: FirebaseClient | None = None
    ):
        self.bot = bot
        self.recipe_manager = recipe_manager
        self.callback_delim = callback_delimiter
        if firebase_client is None:
            self.firebase_client = FirebaseClient(realtime_db_url=secret(self.firebase_env))

    def get_setting_options_menu(self, setting_name: str):
        setting_data = self.settings[setting_name]
        keyboard = InlineKeyboardMarkup()
        keyboard_buttons = []
        for setting_option in setting_data.options:
            button = InlineButton(
                text=str(setting_option).capitalize(),
                callback_data=f'option{self.callback_delim}{setting_name}{self.callback_delim}{setting_option}'
            )
            keyboard_buttons.append(button)
        keyboard.row(*keyboard_buttons)

        return {
            'text': setting_data.query_message,
            'reply_markup': keyboard
        }

    def handle_user_setting_callback(self, call_data: str, message: types.Message, chat_id: int):
        """
        Handles the callback of the user setting selection. Sets the user setting and sends a confirmation message.

        Args:
            call_data (str): The data from the callback query.
            message (types.Message): The original message object used to edit the message and access user data.
            chat_id (int): The chat ID of the user.
        """
        # chat_id = message.chat.id
        setting_name, setting_option = call_data.split(self.callback_delim)
        setting_option = self._try_convert_str_to_int(setting_option)
        self.set_user_setting(chat_id=chat_id, setting_name=setting_name, setting_option=setting_option)

        setting_type = self.settings[setting_name]
        response = self.get_option_confirmation_message(setting_type=setting_type, option=setting_option, chat_id=chat_id)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message.message_id, text=response)

    def get_option_confirmation_message(self, setting_type: SettingsType, option: str | int, chat_id: int | None = None):
        """ 
        Returns a confirmation message for the selected setting option
        
        Args:
            setting_type (SettingsType): The setting type.
            option (str | int): The selected option value.
            chat_id (int | None): The chat ID (optional).
        """
        if setting_type.option_labels and option in setting_type.option_labels:
            option = setting_type.option_labels[option]
        response = setting_type.confirmation_message.format(value=option)

        if setting_type.is_filter:
            user_settings = self.get_user_settings(chat_id=chat_id)
            num_meal_options = self.get_num_of_options(user_settings=user_settings)
            response += f"\n\nEs gibt insgesamt {num_meal_options} passende Gerichte für deine Einstellungen."
        return response

    def set_user_setting(self, chat_id: int, setting_name: str, setting_option: str | int):
        """ Sets a specific user setting in the Firebase database. """
        ref = f"{self.user_settings_ref}/{chat_id}/{setting_name}"
        self.firebase_client.set_entry(
            ref=ref,
            data={'value': setting_option},
        )

    def get_user_settings(self, chat_id: int) -> UserSettings:
        """ Loads the user settings from the Firebase database. """
        ref = f"{self.user_settings_ref}/{chat_id}"
        user_settings_raw = self.firebase_client.get_entry(ref=ref)
        if not user_settings_raw:
            return UserSettings()
        user_settings_data = {}
        for setting_name, setting_data in self.settings.items():
            setting_value = user_settings_raw.get(setting_name, {}).get('value', setting_data.default_value)
            setting_value = self._try_convert_str_to_int(setting_value)
            user_settings_data[setting_name] = setting_value
        user_settings = UserSettings(**user_settings_data)
        return user_settings

    def get_num_of_options(self, user_settings):
        recipes_df = self.recipe_manager.get_recipes_filtered_by_user_settings(user_settings=user_settings)
        num_options = len(recipes_df)
        return num_options

    @staticmethod
    def _try_convert_str_to_int(value: str):
        try:
            value = int(value)
        except ValueError:
            pass
        return value