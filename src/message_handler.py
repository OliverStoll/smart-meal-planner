from utils.logger import create_logger
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as InlineButton


class MessageHandler:
    log = create_logger("Message Handler")

    def __init__(self, options_handler, meal_manager, bot):
        self.options_handler = options_handler
        self.meal_manager = meal_manager
        self.bot = bot
        # persistent data
        self.last_recipes_df = {}
        self.last_message_ids = {}

    def _get_title_response(self, num_meals, meal_type, portions):
        emoji = '🍲' if meal_type == 'alle' else '🥦' if meal_type == 'vegetarisch' else '🌱'
        title_response = (f"**{emoji} Hier sind die Zutaten für {num_meals} "
                          f"{meal_type + 'en ' if meal_type != 'alle' else ''}Gerichte "
                          f"á {portions} Portionen:**\n")
        return title_response

    def send_meals_message(self, chat_id: int, num_meals: int, message_id=None, recipes_to_send=None):
        """ 
        Sends the meal recipes and shopping list to the user.
        
        Args:
            chat_id: The chat ID of the user.
            num_meals: The number of meals to send.
            message_id: The message ID of the previous message (optional).
            recipes_to_send: The recipes to send (optional).
        """
        # todo: remove all sent recipes
        portions, meal_type, max_duration, cal_min = self.options_handler.get_user_options(chat_id)
        if recipes_to_send is None:
            recipes_to_send = self.meal_manager.get_recipes_filtered_by_user_settings(
                num_meals, meal_type, max_duration, cal_min
            )
        self.last_recipes_df[str(chat_id)] = recipes_to_send
        ingredient_shopping_list = self.meal_manager.get_ingredients_shopping_list(recipes_to_send, portions)
        title_response = self._get_title_response(num_meals, meal_type, portions)
        message_data = {
            'chat_id': chat_id,
            'text': f"{title_response}```\n{ingredient_shopping_list}```",
            'parse_mode': 'Markdown',
            'reply_markup': InlineKeyboardMarkup()
        }
        if message_id:
            ingredient_msg = self.bot.edit_message_text(message_id=message_id, **message_data)
        else:
            ingredient_msg = self.bot.send_message(**message_data)
        recipes_pdf_paths = self.meal_manager.get_pdf_paths_from_recipes(recipes_to_send, portions)
        for idx, recipe_pdf_path in enumerate(recipes_pdf_paths):
            try:
                with open(recipe_pdf_path, 'rb') as recipe_file:
                    keyboard = InlineKeyboardMarkup()
                    keyboard.row(
                        InlineButton(
                            text='🔄 Austauschen',
                            callback_data=f'replace_{idx}_{ingredient_msg.message_id}'
                        )
                    )
                    self.bot.send_document(chat_id=chat_id, document=recipe_file, reply_markup=keyboard)
            except FileNotFoundError:
                self.log.error(f"PDF not found: {recipe_pdf_path}")
                self.bot.send_message(chat_id=chat_id, text="PDF nicht gefunden!")

    def replace_meal(self, call, idx, ingredient_msg_id):
        chat_id = call.message.chat.id
        if self.last_recipes_df.get(str(chat_id), None) is None:
            return
        chat_id = call.message.chat.id
        portions, meal_type, max_duration, cal_min = self.options_handler.get_user_options(chat_id)
        last_recipes = self.last_recipes_df[str(chat_id)]
        new_recipe = self.meal_manager.get_recipes_filtered_by_user_settings(1, meal_type, max_duration, cal_min)
        last_recipes.loc[idx] = new_recipe.iloc[0]
        self.bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)

        self.send_meals_message(
            chat_id=chat_id,
            num_meals=len(last_recipes),
            message_id=ingredient_msg_id,
            recipes_to_send=last_recipes,
        )


