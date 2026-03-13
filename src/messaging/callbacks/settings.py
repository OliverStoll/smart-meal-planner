from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton
from common_utils.apis.firebase import FirebaseClient
from common_utils.config import secret

from src.messaging.callbacks.settings_types import SettingsProperties, UserSettings


class SettingsHandler:
    user_settings_path = "data/options.json"
    user_settings_ref = "AppData/Telegram Meal Bot/User Settings"
    firebase_env = "FIREBASE_REALTIME_DB_URL"
    settings: dict[str, SettingsProperties] = {
        "portions": SettingsProperties(
            name="portions",
            friendly_name="Portionsanzahl",
            options=[1, 2, 3, 4, 5, 6],
            default_value=2,
            query_message="🍽️ Wähle die Anzahl der Portionen pro Gericht:",
            confirmation_message="🍽️ Du erhältst jetzt Rezepte für {value} Portionen.",
        ),
        "meal_type": SettingsProperties(
            name="meal_type",
            friendly_name="Art der Gerichte",
            options=["alle", "vegetarisch", "vegan", "protein"],
            default_value="alle",
            query_message="🥗 Wähle die Art der Gerichte:",
            confirmation_message="🥗 Du erhältst jetzt {value} Gerichte.",
            option_labels={
                "alle": "alle",
                "vegetarisch": "vegetarische",
                "vegan": "vegane",
                "protein": "proteinreiche",
            },
            is_filter=True,
        ),
        "max_duration": SettingsProperties(
            name="max_duration",
            friendly_name="Kochzeit",
            options=[10, 15, 20, 25, 30, 45, 60, 90],
            default_value=120,
            query_message="⏱️ Wähle die maximale Kochzeit (in Minuten):",
            confirmation_message="⏱️ Deine maximale Kochzeit beträgt {value} Minuten.",
            is_filter=True,
        ),
        "cal_min": SettingsProperties(
            name="cal_min",
            friendly_name="Kalorien (min.)",
            options=[0, 500, 600, 700, 800, 900],
            default_value=0,
            query_message="🔥 Wähle die minimalen Kalorien pro Portion:",
            confirmation_message="🔥 Du erhältst jetzt Gerichte mit mindestens {value} kcal pro Portion.",
            is_filter=True,
        ),
    }

    def __init__(self, callback_delimiter: str, firebase_client: FirebaseClient | None = None):
        self.callback_delim = callback_delimiter
        if firebase_client is None:
            self.firebase_client = FirebaseClient(realtime_db_url=secret(self.firebase_env))

    def get_setting_options_menu(self, setting_name: str):
        setting_data = self.settings.get(setting_name, None)
        if not setting_data:
            return None
        keyboard = InlineKeyboardMarkup()
        keyboard_buttons = []
        for setting_option in setting_data.options:
            button = InlineButton(
                text=str(setting_option).capitalize(),
                callback_data=f"option{self.callback_delim}{setting_name}{self.callback_delim}{setting_option}",
            )
            keyboard_buttons.append(button)
        keyboard.row(*keyboard_buttons)

        return {"text": setting_data.query_message, "reply_markup": keyboard}

    def handle_setting_user_setting_option(self, call_data: str, chat_id: int) -> tuple[str, str | int]:
        """
        Handles the callback of the user setting selection. Sets the user setting and get the Setting Type object.

        Args:
            call_data (str): The data from the callback query.
            chat_id (int): The chat ID of the user.

        Returns:
            tuple[str, str | int]: The setting name and the selected option value.
        """
        # chat_id = message.chat.id
        setting_name, setting_option = call_data.split(self.callback_delim)
        setting_option = self._try_convert_str_to_int(setting_option)
        self.set_user_setting(chat_id=chat_id, setting_name=setting_name, setting_option=setting_option)

        return setting_name, setting_option

    def get_setting_option_confirmation_message(self, setting_name: str, option_value: str | int):
        """
        Returns a confirmation message for the selected setting option

        Args:
            setting_name (str): The name of the setting.
            option_value (str | int): The selected option value.
            chat_id (int | None): The chat ID (optional).
        """
        setting_properties = self.get_setting_properties(setting_name)
        if setting_properties.option_labels and option_value in setting_properties.option_labels:
            option_value = setting_properties.option_labels[option_value]
        response = setting_properties.confirmation_message.format(value=option_value)
        return response

    @staticmethod
    def get_complete_filter_confirmation_message(num_meal_options: int) -> str:
        message = f"Es gibt insgesamt {num_meal_options} passende Gerichte für deine Einstellungen."
        return message

    def get_setting_properties(self, setting_name: str) -> SettingsProperties | None:
        """
        Returns the SettingsType object for the given setting name.

        Args:
            setting_name (str): The name of the setting.

        Returns:
            SettingsProperties: The SettingsType object.
        """
        return self.settings.get(setting_name, None)

    def set_user_setting(self, chat_id: int, setting_name: str, setting_option: str | int):
        """Sets a specific user setting in the Firebase database."""
        ref = f"{self.user_settings_ref}/{chat_id}/{setting_name}"
        self.firebase_client.set_entry(
            ref=ref,
            data={"value": setting_option},
        )

    def get_user_settings(self, chat_id: int) -> UserSettings:
        """Loads the user settings from the Firebase database."""
        ref = f"{self.user_settings_ref}/{chat_id}"
        user_settings_raw = self.firebase_client.get_entry(ref=ref)
        if not user_settings_raw:
            return UserSettings()
        user_settings_data = {}
        for setting_name, setting_data in self.settings.items():
            setting_value = user_settings_raw.get(setting_name, {}).get("value", setting_data.default_value)
            setting_value = self._try_convert_str_to_int(setting_value)
            user_settings_data[setting_name] = setting_value
        user_settings = UserSettings(**user_settings_data)
        return user_settings

    @staticmethod
    def _try_convert_str_to_int(value: str):
        try:
            value = int(value)
        except ValueError:
            pass
        return value
