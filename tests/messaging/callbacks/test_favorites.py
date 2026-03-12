import pytest
from unittest.mock import MagicMock, patch

from messaging.callbacks.favorites import FavoritesHandler


@pytest.fixture
def mock_firebase():
    return MagicMock()


@pytest.fixture
def favorites_handler(mock_firebase):
    handler = FavoritesHandler()
    handler.firebase_client = mock_firebase
    return handler


class TestFavorizeRecipe:
    def test_calls_firebase_set_entry(self, favorites_handler, mock_firebase):
        favorites_handler.favorize_recipe(chat_id=123, recipe_id="abc")
        mock_firebase.set_entry.assert_called_once()

    def test_uses_correct_firebase_ref(self, favorites_handler, mock_firebase):
        favorites_handler.favorize_recipe(chat_id=123, recipe_id="recipe_abc")
        call_kwargs = mock_firebase.set_entry.call_args.kwargs
        assert "123" in call_kwargs["ref"]
        assert "recipe_abc" in call_kwargs["ref"]

    def test_sets_favorite_true(self, favorites_handler, mock_firebase):
        favorites_handler.favorize_recipe(chat_id=456, recipe_id="xyz")
        call_kwargs = mock_firebase.set_entry.call_args.kwargs
        assert call_kwargs["data"] == {"favorite": True}


class TestUnfavorizeRecipe:
    def test_calls_firebase_delete_entry(self, favorites_handler, mock_firebase):
        favorites_handler.unfavorize_recipe(chat_id=123, recipe_id="abc")
        mock_firebase.delete_entry.assert_called_once()

    def test_uses_correct_firebase_ref(self, favorites_handler, mock_firebase):
        favorites_handler.unfavorize_recipe(chat_id=123, recipe_id="recipe_abc")
        call_args = mock_firebase.delete_entry.call_args.args
        ref = call_args[0] if call_args else mock_firebase.delete_entry.call_args.kwargs.get("ref", "")
        assert "123" in ref
        assert "recipe_abc" in ref


class TestGetFavorites:
    def test_returns_list_of_ids(self, favorites_handler, mock_firebase):
        mock_firebase.get_entry.return_value = {
            "recipe_1": {"favorite": True},
            "recipe_2": {"favorite": True},
        }
        result = favorites_handler.get_favorites(chat_id=123)
        assert isinstance(result, list)
        assert "recipe_1" in result
        assert "recipe_2" in result

    def test_returns_empty_list_when_no_favorites(self, favorites_handler, mock_firebase):
        mock_firebase.get_entry.return_value = None
        result = favorites_handler.get_favorites(chat_id=123)
        assert result == []

    def test_returns_empty_list_for_empty_dict(self, favorites_handler, mock_firebase):
        mock_firebase.get_entry.return_value = {}
        result = favorites_handler.get_favorites(chat_id=123)
        assert result == []

    def test_calls_firebase_with_correct_ref(self, favorites_handler, mock_firebase):
        mock_firebase.get_entry.return_value = None
        favorites_handler.get_favorites(chat_id=789)
        call_args = mock_firebase.get_entry.call_args
        ref = call_args.args[0] if call_args.args else call_args.kwargs.get("ref", "")
        assert "789" in ref
