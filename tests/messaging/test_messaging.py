import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call
from io import BytesIO

from messaging.messaging import MessageHandler, PdfMessageHandler
from messaging.callbacks.settings_types import UserSettings


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_recipes_df():
    return pd.DataFrame({
        "id": ["r1", "r2", "r3"],
        "title": ["Pasta Primavera", "Veggie Burger", "Steak"],
        "tags": ["vegetarisch", "vegan", "protein"],
        "total_time": [30, 25, 45],
        "calories": [600, 500, 800],
    })


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    sent_message = MagicMock()
    sent_message.message_id = 42
    bot.send_message.return_value = sent_message
    bot.edit_message_text.return_value = sent_message
    bot.send_document.return_value = sent_message
    return bot


@pytest.fixture
def mock_settings_handler():
    handler = MagicMock()
    handler.get_user_settings.return_value = UserSettings(
        portions=2, meal_type="alle", max_duration=120, cal_min=0
    )
    return handler


@pytest.fixture
def mock_recipe_handler(sample_recipes_df):
    handler = MagicMock()
    handler.raw_recipes = sample_recipes_df
    handler.sample_fitting_recipes.return_value = sample_recipes_df.copy()
    handler.get_ingredients_shopping_list.return_value = "200 g  Pasta\n100 g  Tofu\n"
    return handler


@pytest.fixture
def mock_favorites_handler():
    handler = MagicMock()
    handler.get_favorites.return_value = ["r1"]
    return handler


@pytest.fixture
def message_handler(mock_bot, mock_settings_handler, mock_recipe_handler, mock_favorites_handler):
    with patch("messaging.messaging.PdfMessageHandler"):
        handler = MessageHandler(
            settings_handler=mock_settings_handler,
            recipe_handler=mock_recipe_handler,
            favorites_handler=mock_favorites_handler,
            bot=mock_bot,
        )
    return handler


@pytest.fixture
def pdf_message_handler(mock_bot, sample_recipes_df):
    return PdfMessageHandler(bot=mock_bot, recipes=sample_recipes_df)


# ---------------------------------------------------------------------------
# MessageHandler._get_shopping_list_title
# ---------------------------------------------------------------------------

class TestGetShoppingListTitle:
    def test_contains_num_meals(self, message_handler):
        title = message_handler._get_shopping_list_title(num_meals=3, meal_type="alle", portions=2)
        assert "3" in title

    def test_contains_portions(self, message_handler):
        title = message_handler._get_shopping_list_title(num_meals=2, meal_type="alle", portions=4)
        assert "4" in title

    def test_contains_meal_type_label(self, message_handler):
        title = message_handler._get_shopping_list_title(num_meals=2, meal_type="vegan", portions=2)
        assert "vegane" in title

    def test_contains_vegetarisch_label(self, message_handler):
        title = message_handler._get_shopping_list_title(num_meals=2, meal_type="vegetarisch", portions=2)
        assert "vegetarische" in title

    def test_alle_has_no_extra_label(self, message_handler):
        title = message_handler._get_shopping_list_title(num_meals=2, meal_type="alle", portions=2)
        # "alle" maps to empty string - should not appear as "alle Gerichte"
        assert "alle Gerichte" not in title

    def test_returns_string(self, message_handler):
        result = message_handler._get_shopping_list_title(num_meals=2, meal_type="alle", portions=2)
        assert isinstance(result, str)

    def test_unknown_meal_type_uses_default_emoji(self, message_handler):
        title = message_handler._get_shopping_list_title(num_meals=2, meal_type="unknown", portions=2)
        assert "🍲" in title


# ---------------------------------------------------------------------------
# MessageHandler.send_shopping_list_message
# ---------------------------------------------------------------------------

class TestSendShoppingListMessage:
    def test_sends_new_message_without_replace_id(self, message_handler, mock_bot):
        user_settings = UserSettings()
        message_handler.send_shopping_list_message(
            chat_id=123,
            num_meals=2,
            shopping_list_ingredients="200 g Pasta\n",
            user_settings=user_settings,
            replace_message_id=None,
        )
        mock_bot.send_message.assert_called_once()

    def test_edits_existing_message_with_replace_id(self, message_handler, mock_bot):
        user_settings = UserSettings()
        message_handler.send_shopping_list_message(
            chat_id=123,
            num_meals=2,
            shopping_list_ingredients="200 g Pasta\n",
            user_settings=user_settings,
            replace_message_id=99,
        )
        mock_bot.edit_message_text.assert_called_once()
        mock_bot.send_message.assert_not_called()

    def test_returns_message_object(self, message_handler, mock_bot):
        user_settings = UserSettings()
        result = message_handler.send_shopping_list_message(
            chat_id=123,
            num_meals=2,
            shopping_list_ingredients="200 g Pasta\n",
            user_settings=user_settings,
            replace_message_id=None,
        )
        assert result is not None

    def test_message_contains_ingredients(self, message_handler, mock_bot):
        user_settings = UserSettings()
        message_handler.send_shopping_list_message(
            chat_id=123,
            num_meals=2,
            shopping_list_ingredients="200 g Pasta\n",
            user_settings=user_settings,
            replace_message_id=None,
        )
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "200 g Pasta" in call_kwargs["text"]


# ---------------------------------------------------------------------------
# MessageHandler.send_full_recipes_message
# ---------------------------------------------------------------------------

class TestSendFullRecipesMessage:
    def test_no_message_sent_for_zero_meals(self, message_handler, mock_bot):
        message_handler.send_full_recipes_message(chat_id=123, num_meals=0)
        mock_bot.send_message.assert_not_called()

    def test_logs_error_when_neither_recipes_nor_meals(self, message_handler, mock_bot):
        message_handler.send_full_recipes_message(chat_id=123)
        mock_bot.send_message.assert_not_called()

    def test_calls_send_shopping_list_message(self, message_handler, mock_bot):
        with patch.object(message_handler, "send_shopping_list_message", wraps=message_handler.send_shopping_list_message) as spy:
            message_handler.send_full_recipes_message(chat_id=123, num_meals=2)
            spy.assert_called_once()

    def test_stores_last_sent_recipes(self, message_handler, mock_recipe_handler, sample_recipes_df):
        message_handler.send_full_recipes_message(chat_id=123, num_meals=2)
        assert "123" in message_handler.last_sent_recipes_df

    def test_uses_provided_recipes_df(self, message_handler, mock_recipe_handler, sample_recipes_df):
        custom_df = sample_recipes_df.head(1).copy()
        message_handler.send_full_recipes_message(
            chat_id=123,
            recipes_to_send=custom_df,
        )
        # sample_fitting_recipes should NOT be called since recipes were provided
        mock_recipe_handler.sample_fitting_recipes.assert_not_called()


# ---------------------------------------------------------------------------
# MessageHandler.replace_single_recipe_in_data
# ---------------------------------------------------------------------------

class TestReplaceSingleRecipeInData:
    def test_replaces_recipe_at_correct_index(self, message_handler, mock_recipe_handler, sample_recipes_df):
        new_recipe_df = pd.DataFrame({
            "id": ["r_new"],
            "title": ["New Recipe"],
            "tags": ["alle"],
            "total_time": [20],
            "calories": [700],
        })
        mock_recipe_handler.sample_fitting_recipes.return_value = new_recipe_df

        updated_df, replaced_idx = message_handler.replace_single_recipe_in_data(
            last_sent_recipes=sample_recipes_df.copy(),
            chat_id=123,
            recipe_id="r1",
        )
        assert "r_new" in updated_df["id"].values

    def test_returns_correct_replaced_index(self, message_handler, mock_recipe_handler, sample_recipes_df):
        new_recipe_df = pd.DataFrame({
            "id": ["r_new"],
            "title": ["New Recipe"],
            "tags": ["alle"],
            "total_time": [20],
            "calories": [700],
        })
        mock_recipe_handler.sample_fitting_recipes.return_value = new_recipe_df

        _, replaced_idx = message_handler.replace_single_recipe_in_data(
            last_sent_recipes=sample_recipes_df.copy(),
            chat_id=123,
            recipe_id="r2",
        )
        # r2 is at index 1 in the default DataFrame
        assert replaced_idx == 1

    def test_dataframe_length_unchanged(self, message_handler, mock_recipe_handler, sample_recipes_df):
        new_recipe_df = pd.DataFrame({
            "id": ["r_new"],
            "title": ["New Recipe"],
            "tags": ["alle"],
            "total_time": [20],
            "calories": [700],
        })
        mock_recipe_handler.sample_fitting_recipes.return_value = new_recipe_df

        updated_df, _ = message_handler.replace_single_recipe_in_data(
            last_sent_recipes=sample_recipes_df.copy(),
            chat_id=123,
            recipe_id="r1",
        )
        assert len(updated_df) == len(sample_recipes_df)


# ---------------------------------------------------------------------------
# MessageHandler.resend_messages_to_replace_meal
# ---------------------------------------------------------------------------

class TestResendMessagesToReplaceMeal:
    def test_raises_when_no_previous_recipes(self, message_handler):
        with pytest.raises(ValueError):
            message_handler.resend_messages_to_replace_meal(
                message_id=10,
                chat_id=999,
                related_shopping_list_message_id=5,
                recipe_id="r1",
            )

    def test_deletes_original_message(self, message_handler, mock_bot, mock_recipe_handler, sample_recipes_df):
        new_recipe_df = pd.DataFrame({
            "id": ["r_new"], "title": ["New"], "tags": ["alle"],
            "total_time": [20], "calories": [500],
        })
        mock_recipe_handler.sample_fitting_recipes.return_value = new_recipe_df
        message_handler.last_sent_recipes_df["123"] = sample_recipes_df.copy()

        with patch.object(message_handler, "send_full_recipes_message"):
            message_handler.resend_messages_to_replace_meal(
                message_id=10,
                chat_id=123,
                related_shopping_list_message_id=5,
                recipe_id="r1",
            )
        mock_bot.delete_message.assert_called_once_with(chat_id=123, message_id=10)

    def test_calls_send_full_recipes_message_after_delete(
        self, message_handler, mock_bot, mock_recipe_handler, sample_recipes_df
    ):
        new_recipe_df = pd.DataFrame({
            "id": ["r_new"], "title": ["New"], "tags": ["alle"],
            "total_time": [20], "calories": [500],
        })
        mock_recipe_handler.sample_fitting_recipes.return_value = new_recipe_df
        message_handler.last_sent_recipes_df["123"] = sample_recipes_df.copy()

        with patch.object(message_handler, "send_full_recipes_message") as mock_send:
            message_handler.resend_messages_to_replace_meal(
                message_id=10,
                chat_id=123,
                related_shopping_list_message_id=5,
                recipe_id="r1",
            )
        mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# PdfMessageHandler._get_pdf_id_to_title_mapping
# ---------------------------------------------------------------------------

class TestGetPdfIdToTitleMapping:
    def test_maps_id_to_title(self, sample_recipes_df):
        mapping = PdfMessageHandler._get_pdf_id_to_title_mapping(sample_recipes_df)
        assert mapping["r1"] == "Pasta Primavera"
        assert mapping["r2"] == "Veggie Burger"
        assert mapping["r3"] == "Steak"

    def test_empty_dataframe_returns_empty_dict(self):
        empty_df = pd.DataFrame({"id": [], "title": []})
        mapping = PdfMessageHandler._get_pdf_id_to_title_mapping(empty_df)
        assert mapping == {}

    def test_returns_dict(self, sample_recipes_df):
        mapping = PdfMessageHandler._get_pdf_id_to_title_mapping(sample_recipes_df)
        assert isinstance(mapping, dict)


# ---------------------------------------------------------------------------
# PdfMessageHandler._get_pdf_path
# ---------------------------------------------------------------------------

class TestGetPdfPath:
    def test_returns_correct_path(self, pdf_message_handler):
        path = pdf_message_handler._get_pdf_path(recipe_id="r1", num_portions=2)
        assert "Pasta Primavera" in path
        assert "2" in path
        assert path.endswith(".pdf")

    def test_returns_none_for_unknown_id(self, pdf_message_handler):
        path = pdf_message_handler._get_pdf_path(recipe_id="nonexistent", num_portions=2)
        assert path is None

    def test_path_contains_pdf_dir(self, pdf_message_handler):
        path = pdf_message_handler._get_pdf_path(recipe_id="r2", num_portions=4)
        assert "temp_pdfs" in path


# ---------------------------------------------------------------------------
# PdfMessageHandler._create_pdf_inline_keyboard
# ---------------------------------------------------------------------------

class TestCreatePdfInlineKeyboard:
    def test_keyboard_has_two_buttons(self):
        keyboard = PdfMessageHandler._create_pdf_inline_keyboard(
            shopping_list_message_id=1, recipe_id="r1", is_favorite=False
        )
        assert len(keyboard.keyboard) == 1
        assert len(keyboard.keyboard[0]) == 2

    def test_replace_button_callback_contains_recipe_id(self):
        keyboard = PdfMessageHandler._create_pdf_inline_keyboard(
            shopping_list_message_id=10, recipe_id="r1", is_favorite=False
        )
        replace_btn = keyboard.keyboard[0][0]
        assert "r1" in replace_btn.callback_data
        assert "replace" in replace_btn.callback_data

    def test_favorite_button_callback_for_non_favorite(self):
        keyboard = PdfMessageHandler._create_pdf_inline_keyboard(
            shopping_list_message_id=10, recipe_id="r1", is_favorite=False
        )
        fav_btn = keyboard.keyboard[0][1]
        assert "favorite" in fav_btn.callback_data
        assert "unfavorite" not in fav_btn.callback_data

    def test_unfavorite_button_callback_for_favorite(self):
        keyboard = PdfMessageHandler._create_pdf_inline_keyboard(
            shopping_list_message_id=10, recipe_id="r1", is_favorite=True
        )
        fav_btn = keyboard.keyboard[0][1]
        assert "unfavorite" in fav_btn.callback_data

    def test_replace_button_contains_shopping_list_message_id(self):
        keyboard = PdfMessageHandler._create_pdf_inline_keyboard(
            shopping_list_message_id=42, recipe_id="r1", is_favorite=False
        )
        replace_btn = keyboard.keyboard[0][0]
        assert "42" in replace_btn.callback_data

    def test_keyboard_without_shopping_list_message_id(self):
        keyboard = PdfMessageHandler._create_pdf_inline_keyboard(
            shopping_list_message_id=None, recipe_id="r1", is_favorite=False
        )
        replace_btn = keyboard.keyboard[0][0]
        assert "None" in replace_btn.callback_data


# ---------------------------------------------------------------------------
# PdfMessageHandler.send_single_recipe_pdf
# ---------------------------------------------------------------------------

class TestSendSingleRecipePdf:
    def test_sends_document_when_pdf_exists(self, pdf_message_handler, mock_bot, tmp_path):
        # Create a fake PDF file
        pdf_dir = tmp_path / "2"
        pdf_dir.mkdir(parents=True)
        fake_pdf = pdf_dir / "Pasta Primavera.pdf"
        fake_pdf.write_bytes(b"%PDF fake content")

        pdf_message_handler.recipe_pdf_dir = str(tmp_path)
        pdf_message_handler.thumbnail_dir = str(tmp_path)

        pdf_message_handler.send_single_recipe_pdf(
            chat_id=123,
            recipe_id="r1",
            num_portions=2,
            shopping_list_message_id=10,
            is_favorite=False,
        )
        mock_bot.send_document.assert_called_once()

    def test_sends_message_when_pdf_not_found(self, pdf_message_handler, mock_bot):
        pdf_message_handler.recipe_pdf_dir = "/nonexistent/path"
        pdf_message_handler.send_single_recipe_pdf(
            chat_id=123,
            recipe_id="r1",
            num_portions=2,
            shopping_list_message_id=10,
            is_favorite=False,
        )
        mock_bot.send_message.assert_called_once()

    def test_returns_message_id(self, pdf_message_handler, mock_bot):
        pdf_message_handler.recipe_pdf_dir = "/nonexistent/path"
        result = pdf_message_handler.send_single_recipe_pdf(
            chat_id=123,
            recipe_id="r1",
            num_portions=2,
        )
        assert result == mock_bot.send_message.return_value.message_id


# ---------------------------------------------------------------------------
# PdfMessageHandler.send_multiple_recipe_pdfs
# ---------------------------------------------------------------------------

class TestSendMultipleRecipePdfs:
    def test_calls_send_single_for_each_recipe(self, pdf_message_handler, mock_bot):
        pdf_message_handler.recipe_pdf_dir = "/nonexistent/path"
        recipe_ids = ["r1", "r2", "r3"]
        pdf_message_handler.send_multiple_recipe_pdfs(
            chat_id=123,
            recipe_ids=recipe_ids,
            num_portions=2,
            shopping_list_message_id=10,
            favorites_ids=[],
        )
        assert mock_bot.send_message.call_count == 3

    def test_returns_list_of_message_ids(self, pdf_message_handler, mock_bot):
        pdf_message_handler.recipe_pdf_dir = "/nonexistent/path"
        result = pdf_message_handler.send_multiple_recipe_pdfs(
            chat_id=123,
            recipe_ids=["r1", "r2"],
            num_portions=2,
        )
        assert isinstance(result, list)
        assert len(result) == 2

    def test_marks_favorites_correctly(self, pdf_message_handler, mock_bot):
        pdf_message_handler.recipe_pdf_dir = "/nonexistent/path"
        with patch.object(
            pdf_message_handler, "send_single_recipe_pdf", wraps=pdf_message_handler.send_single_recipe_pdf
        ) as spy:
            pdf_message_handler.send_multiple_recipe_pdfs(
                chat_id=123,
                recipe_ids=["r1", "r2"],
                num_portions=2,
                favorites_ids=["r1"],
            )
            calls = spy.call_args_list
            # r1 is a favorite, r2 is not
            assert calls[0].kwargs["is_favorite"] is True
            assert calls[1].kwargs["is_favorite"] is False

    def test_returns_empty_list_for_no_recipes(self, pdf_message_handler, mock_bot):
        result = pdf_message_handler.send_multiple_recipe_pdfs(
            chat_id=123,
            recipe_ids=[],
            num_portions=2,
        )
        assert result == []
