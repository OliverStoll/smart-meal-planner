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
        title_response = (f"**{emoji} Hier {'sind' if num_meals > 1 else 'ist'} {num_meals} "
                          f"{meal_type + 'en ' if meal_type != 'alle' else ''}Gerichte "
                          f"á {portions} Portionen:**")
        return title_response

    def _get_replace_keyboard(self, num_meals, recipes):
        keyboard = InlineKeyboardMarkup()
        buttons = [*[InlineButton(f"{recipes.iloc[i]['title']}..",
                                  callback_data=f'replace_{i}') for i in range(num_meals)],
                   InlineButton('-', callback_data='delete')]
        if len(buttons) <= 4:
            keyboard.row(*buttons)
        else:
            keyboard.row(*buttons[:4])
            keyboard.row(*buttons[4:])
        return keyboard

    def send_meals_message(self, chat_id, num_meals, recipes=None):
        portions, meal_type, max_duration, cal_min = self.options_handler.get_user_options(chat_id)

        if recipes is None:
            self.bot.delete_last_message(chat_id)
            recipes = self.meal_manager.get_recipes_filtered_by_user_settings(
                num_meals, meal_type, max_duration, cal_min
            )
        self.last_recipes_df[str(chat_id)] = recipes
        ingredient_shopping_list = self.meal_manager.get_ingredients_shopping_list(recipes, portions)
        recipes_pdf_paths = self.meal_manager.get_pdf_paths_from_recipes(recipes, portions)

        title_response = self._get_title_response(num_meals, meal_type, portions)
        first_msg = self.bot.send_message(chat_id=chat_id, text=title_response, parse_mode='Markdown')

        response = f"```\n{ingredient_shopping_list}```"
        self.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')

        # send PDFs
        for idx, pdf in enumerate(recipes_pdf_paths):
            try:
                with open(pdf, 'rb') as file:
                    self.bot.send_document(chat_id=chat_id, document=file)
            except FileNotFoundError:
                self.log.error(f"PDF not found: {pdf}")
                self.bot.send_message(chat_id=chat_id, text="PDF nicht gefunden!")

        response = "🔄 Ein Gericht austauschen?"
        keyboard = self._get_replace_keyboard(num_meals, recipes)
        last_msg = self.bot.send_message(chat_id=chat_id, text=response, reply_markup=keyboard)
        self.last_message_ids[str(chat_id)] = (first_msg.message_id, last_msg.message_id)


    def replace_meal(self, call, idx):
        chat_id = call.message.chat.id
        if self.last_recipes_df.get(str(chat_id), None) is None:
            return
        chat_id = call.message.chat.id
        portions, meal_type, max_duration, cal_min = self.options_handler.get_user_options(chat_id)
        recipes = self.last_recipes_df[str(chat_id)]
        new_recipe = self.meal_manager.get_recipes_filtered_by_user_settings(1, meal_type, max_duration, cal_min)
        recipes.loc[idx] = new_recipe.iloc[0]
        last_msg_ids = self.last_message_ids.get(str(chat_id), None)
        if isinstance(last_msg_ids, tuple):
            self.bot.delete_messages(
                chat_id=chat_id,
                message_ids=range(last_msg_ids[0], last_msg_ids[1] + 1)
            )
        self.send_meals_message(chat_id, len(recipes), recipes=recipes)


