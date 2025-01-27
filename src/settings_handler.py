import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton


class SettingsHandler:
    user_settings_path = 'data/options.json'
    settings_friendly_names = {
        'portions': 'Portionsanzahl',
        'meal-type': 'Art der Gerichte',
        'max-duration': 'Kochzeit',
        'cal-min': 'Kalorien (min.)'
    }
    settings_query_messages = {
        'portions': 'Wähle die Anzahl der Portionen pro Gericht:',
        'meal-type': 'Wähle die Art der Gerichte:',
        'max-duration': 'Wähle die maximale Kochzeit (in Minuten):',
        'cal-min': 'Wähle die minimalen Calorien pro Portion:'
    }
    setting_query_options = {
        'portions': [1, 2, 3, 4, 5, 6],
        'meal-type': ['alle', 'vegetarisch', 'vegan'],
        'max-duration': [10, 15, 20, 25, 30, 45, 60, 90],
        'cal-min': [500, 600, 700, 800, 900]
    }

    def __init__(self, bot, meal_manager):
        self.bot = bot
        self.meal_manager = meal_manager


    def handle_settings_callback(self, call):
        setting = call.data.replace('settings_', '')
        response = self.settings_query_messages[setting]
        keyboard = InlineKeyboardMarkup()
        keyboard_buttons = [
            InlineButton(f"{str(i).capitalize()}", callback_data=f'option_{setting}_{i}')
            for i in self.setting_query_options[setting]
        ]
        keyboard.row(*keyboard_buttons)
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=response,
            reply_markup=keyboard
        )

    def handle_user_setting_callback(self, call):
        setting_name, setting_value = call.data.replace('option_', '').split('_')
        try:
            setting_value = int(setting_value)
        except ValueError:
            pass
        self.set_user_setting(
            chat_id=call.message.chat.id, setting_name=setting_name, value=setting_value
        )
        response = f"Du hast {self.settings_friendly_names[setting_name]}: {setting_value} eingestellt!"
        if setting_name in ['max-duration', 'meal-type', 'cal-min']:
            num_meal_options = self.get_num_of_options(call.message.chat.id)
            response += f" \nEs gibt insgesamt {num_meal_options} passende Gerichte."
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=response
        )

    def set_user_setting(self, chat_id, setting_name, value):
        with open(self.user_settings_path, 'r') as file:
            options_data = json.load(file)
        options_data[setting_name][str(chat_id)] = value
        with open(self.user_settings_path, 'w') as file:
            json.dump(options_data, file)

    def get_user_options(self, chat_id):
        chat_id = str(chat_id)
        options_file = json.load(open(self.user_settings_path, 'r'))
        portions = options_file['portions'].get(chat_id, 2)
        meal_type = options_file['meal-type'].get(chat_id, 'alle')
        max_duration = options_file['max-duration'].get(chat_id, 120)
        cal_min = options_file['cal-min'].get(chat_id, 0)
        return portions, meal_type, max_duration, cal_min

    def get_num_of_options(self, chat_id):
        options_file = json.load(open(self.user_settings_path, 'r'))
        meal_type = options_file['meal-type'].get(str(chat_id), None)
        max_duration = options_file['max-duration'].get(str(chat_id), 999)
        cal_min = options_file['cal-min'].get(str(chat_id), 0)
        recipes_df = self.meal_manager.get_recipes_filtered_by_user_settings(99999, meal_type, max_duration, cal_min)
        num_options = len(recipes_df)
        return num_options