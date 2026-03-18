import pandas as pd
from telebot import types, TeleBot

from database.engine import recipes_from_sql
from logs.logs import create_logger

from messaging.callbacks.favorites import get_favorite_ids
from messaging.callbacks.settings import get_user_settings
from messaging.pdfs import send_recipe_pdf, send_multiple_recipe_pdfs
from messaging.recipes import sample_recipes
from messaging.ingredients import ingredients_shopping_list

log = create_logger("Message Handler")

TITLE_EMOJI = {
    "alle": "🍲",
    "vegetarisch": "🥦",
    "vegan": "🌱",
    "protein": "🍗",
}
FRIENDLY_MEAL_TYPES = {
    "alle": "",
    "vegetarisch": "vegetarische ",
    "vegan": "vegane ",
    "protein": "proteinreiche ",
}
last_sent_recipes_df: dict[int, pd.DataFrame] = {}


def send_full_message(
    bot: TeleBot,
    chat_id: int,
    num_meals: int | None = None,
    previous_shopping_list_message_id: int | None = None,
    recipes_to_send: pd.DataFrame | None = None,
    recipe_idx_to_replace: int | None = None,
):
    """
    Sends the meal recipes and shopping list to the user.

    Args:
        chat_id: The chat ID of the user.
        num_meals: The number of meals to send. Not required if recipes_to_send is provided.
        previous_shopping_list_message_id: The message ID of the previous message (optional).
        recipes_to_send: The recipes to send (optional).
        recipe_idx_to_replace: The index of the recipe to replace (optional).
    """

    if num_meals == 0:
        log.info("No meals requested, not sending any messages.")
        return
    if recipes_to_send is None and num_meals is None:
        log.error("Either recipes_to_send or num_meals must be provided.")
        return

    user_settings = get_user_settings(chat_id=chat_id)
    num_meals = num_meals or len(recipes_to_send)
    all_recipes = recipes_from_sql()
    if recipes_to_send is None:
        recipes_to_send = sample_recipes(num_recipes=num_meals, user_settings=user_settings, recipes=all_recipes)
    recipe_ids = recipes_to_send["id"].tolist()
    last_sent_recipes_df[chat_id] = recipes_to_send

    ingredients = ingredients_shopping_list(recipes=recipes_to_send, num_portions=user_settings.portions)
    title = shopping_list_title(num_meals=num_meals, meal_type=user_settings.meal_type, portions=num_meals)
    message = send_shopping_list_message(
        bot=bot,
        chat_id=chat_id,
        title=title,
        ingredients=ingredients,
        replace_msg_id=previous_shopping_list_message_id,
    )
    favorites_ids = get_favorite_ids(chat_id)
    if recipe_idx_to_replace is not None:
        recipe_id = recipe_ids[recipe_idx_to_replace]
        send_recipe_pdf(
            bot=bot,
            chat_id=chat_id,
            num_portions=user_settings.portions,
            shopping_list_message_id=message.message_id,
            recipe_id=recipe_id,
            is_favorite=recipe_id in favorites_ids,
        )
    else:
        send_multiple_recipe_pdfs(
            bot=bot,
            chat_id=chat_id,
            recipe_ids=recipe_ids,
            num_portions=user_settings.portions,
            shopping_list_message_id=message.message_id,
            favorites_ids=favorites_ids,
        )


def send_shopping_list_message(
    bot: TeleBot, chat_id: int, title: str, ingredients: str, replace_msg_id: int | None
) -> types.Message:
    """Sends a message with the combined shopping list for the selected recipes."""
    message_args = {
        "text": f"{title}\n```\n{ingredients}```",
        "chat_id": chat_id,
        "parse_mode": "Markdown",
    }
    if replace_msg_id:
        sent_message = bot.edit_message_text(message_id=replace_msg_id, **message_args)
    else:
        sent_message = bot.send_message(**message_args)
    return sent_message


def shopping_list_title(num_meals: int, meal_type: str, portions: int) -> str:
    emoji = TITLE_EMOJI.get(meal_type, "🍲")
    meal_type = FRIENDLY_MEAL_TYPES.get(meal_type, "")
    title_response = f"**{emoji} Hier sind die Zutaten für {num_meals} {meal_type}Gerichte á {portions} Portionen:**"
    return title_response


def replace_single_recipe_in_data(recipes: pd.DataFrame, chat_id: int, recipe_id: str) -> tuple[pd.DataFrame, int]:
    user_settings = get_user_settings(chat_id)
    new_recipe = sample_recipes(num_recipes=1, user_settings=user_settings)
    idx_to_replace = recipes.index[recipes["id"] == recipe_id].tolist()[0]
    recipes.loc[idx_to_replace] = new_recipe.iloc[0]
    return recipes, idx_to_replace


def resend_messages_to_replace_meal(
    bot: TeleBot,
    message_id: int,
    chat_id: int,
    related_shopping_list_message_id: int,
    recipe_id: str,
):
    last_sent_recipes: pd.DataFrame | None = last_sent_recipes_df.get(chat_id, None)
    if last_sent_recipes is None:
        raise ValueError(f"No recipes found for chat ID {chat_id}.")
    updated_recipes, replaced_idx = replace_single_recipe_in_data(
        recipes=last_sent_recipes, chat_id=chat_id, recipe_id=recipe_id
    )
    bot.delete_message(chat_id=chat_id, message_id=message_id)
    send_full_message(
        bot=bot,
        chat_id=chat_id,
        num_meals=len(updated_recipes),
        previous_shopping_list_message_id=related_shopping_list_message_id,
        recipes_to_send=updated_recipes,
        recipe_idx_to_replace=replaced_idx,
    )
