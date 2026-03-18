from logs.logs import create_logger
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup

from database.storage import download_thumbnail, download_pdf
from messaging.keyboard import replace_button, favorize_button

log = create_logger("PDF Message Handler")


def send_multiple_recipe_pdfs(
    bot: TeleBot,
    chat_id: int,
    recipe_ids: list[int],
    num_portions: int,
    shopping_list_message_id: int | None = None,
    favorites_ids: list[str] | None = None,
) -> list[int]:
    """
    Send all recipe PDFs to the user.

    Args:
        chat_id: The chat ID of the user.
        recipe_ids: The IDs of the recipes.
        num_portions: The number of portions.
        shopping_list_message_id: The message id of the shopping list.
        favorites_ids: A list of favorite recipe IDs (optional).

    Returns:
        pdf_message_ids: A list of message IDs for the sent PDFs.
    """

    pdf_message_ids = []
    for idx, recipe_id in enumerate(recipe_ids):
        is_favorite = recipe_id in favorites_ids if favorites_ids else False
        pdf_message_id = send_recipe_pdf(
            bot=bot,
            chat_id=chat_id,
            shopping_list_message_id=shopping_list_message_id,
            recipe_id=recipe_id,
            num_portions=num_portions,
            is_favorite=is_favorite,
        )
        pdf_message_ids.append(pdf_message_id)

    return pdf_message_ids


def send_recipe_pdf(
    bot: TeleBot,
    chat_id: int,
    recipe_id: int,
    num_portions: int,
    shopping_list_message_id: int | None = None,
    is_favorite: bool = False,
) -> int:
    """
    Send a single recipe PDF to the user.

    Args:
        bot: TeleBot
        chat_id: The chat ID of the user.
        shopping_list_message_id: The message id of the shopping list.
        recipe_id: The ID of the recipe.
        num_portions: The number of portions.
        is_favorite: Whether the recipe is a favorite (optional).

    Returns:
        message_id: The message ID of the sent PDF.
    """
    keyboard = pdf_inline_keyboard(
        shopping_list_message_id=shopping_list_message_id,
        recipe_id=recipe_id,
        is_favorite=is_favorite,
    )
    thumbnail_file = download_thumbnail(recipe_id=recipe_id)
    pdf_file = download_pdf(recipe_id=recipe_id, num_portions=num_portions)

    try:
        message = bot.send_document(
            chat_id=chat_id,
            document=pdf_file,
            reply_markup=keyboard,
            thumb=thumbnail_file,
        )
        return message.message_id
    except Exception:
        log.error(f"PDF not found for id {recipe_id}")
        message = bot.send_message(chat_id=chat_id, text="PDF nicht gefunden!", reply_markup=keyboard)
        return message.message_id


def pdf_inline_keyboard(
    shopping_list_message_id: int | None,
    recipe_id: int,
    is_favorite: bool = False,
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    replace_button_ = replace_button(recipe_id=recipe_id, shopping_list_msg_id=shopping_list_message_id)
    keyboard.row(replace_button_, favorize_button(recipe_id=recipe_id, is_favorite=is_favorite))
    return keyboard
