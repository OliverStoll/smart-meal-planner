import json
from dataclasses import dataclass
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from telebot import types

from common_utils.apis.firebase import FirebaseClient
from common_utils.config import secret



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
    callback_delim = '|'
    user_settings_path = 'data/options.json'
    user_settings_ref = 'AppData/Telegram Meal Bot/User Settings'
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

    def __init__(self, bot, meal_manager):
        self.bot = bot
        self.meal_manager = meal_manager
        self.firebase_client = FirebaseClient(realtime_db_url=secret('FIREBASE_REALTIME_DB_URL'))

    def handle_settings_callback(self, setting_name: str, message: types.Message):
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

        self.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=setting_data.query_message,
            reply_markup=keyboard
        )

    def handle_user_setting_callback(self, call_data: str, message: types.Message):
        """
        Handles the callback of the user setting selection. Sets the user setting and sends a confirmation message.

        Args:
            call_data (str): The data from the callback query.
            message (types.Message): The original message object used to edit the message and access user data.
        """
        setting_name, setting_option = call_data.split(self.callback_delim)
        chat_id = message.chat.id
        setting = self.settings[setting_name]
        setting_option = self._try_convert_str_to_int(setting_option)
        self.set_user_setting(chat_id=chat_id, setting_name=setting_name, setting_option=setting_option)

        response = self.get_option_confirmation_message(setting=setting, option=setting_option, chat_id=chat_id)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message.message_id, text=response)

    def get_option_confirmation_message(self, setting: SettingsType, option: str | int, chat_id: int | None = None):
        """ 
        Returns a confirmation message for the selected setting option
        
        Args:
            setting (SettingsType): The setting type.
            option (str | int): The selected option value.
            chat_id (int | None): The chat ID (optional).
        """
        if setting.option_labels and option in setting.option_labels:
            option = setting.option_labels[option]
        response = setting.confirmation_message.format(value=option)

        if setting.is_filter:
            num_meal_options = self.get_num_of_options(chat_id=chat_id)
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

    def get_num_of_options(self, chat_id):
        options_file = json.load(open(self.user_settings_path, 'r'))
        meal_type = options_file['meal_type'].get(str(chat_id), None)
        max_duration = options_file['max_duration'].get(str(chat_id), 999)
        cal_min = options_file['cal_min'].get(str(chat_id), 0)
        portions = options_file['portions'].get(str(chat_id), 2)
        user_settings = UserSettings(
            portions=portions,
            meal_type=meal_type,
            max_duration=max_duration,
            cal_min=cal_min
        )
        recipes_df = self.meal_manager.get_recipes_filtered_by_user_settings(
            num_recipes=999999,
            user_settings=user_settings
        )
        num_options = len(recipes_df)
        return num_options

    @staticmethod
    def _try_convert_str_to_int(value: str):
        try:
            value = int(value)
        except ValueError:
            pass
        return value