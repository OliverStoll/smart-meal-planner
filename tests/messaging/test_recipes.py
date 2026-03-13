import pytest
import pandas as pd
from unittest.mock import patch

from messaging.callbacks.settings_types import UserSettings
from messaging.recipes import RecipeManager


@pytest.fixture
def recipe_manager():
    """Create a RecipeManager with mocked data instead of reading CSV files."""
    sample_recipes = pd.DataFrame(
        {
            "id": ["r1", "r2", "r3", "r4"],
            "title": ["Pasta Primavera", "Veggie Burger", "Steak", "Vegan Bowl"],
            "tags": ["vegetarisch, lecker", "vegetarisch, vegan", "protein, fleisch", "vegan, gesund"],
            "total_time": [30, 25, 45, 20],
            "calories": [600, 500, 800, 400],
            "ingredients": [
                "[{'name': 'Pasta', 'quantity': '200', 'unit': 'g'}]",
                "[{'name': 'Tofu', 'quantity': '100', 'unit': 'g'}]",
                "[{'name': 'Rindfleisch', 'quantity': '250', 'unit': 'g'}]",
                "[{'name': 'Quinoa', 'quantity': '150', 'unit': 'g'}]",
            ],
        }
    )
    sample_ingredients = pd.DataFrame(
        {
            "name": ["Pasta", "Tofu", "Rindfleisch", "Quinoa"],
            "category": ["Haltbares", "Verschiedenes", "Fleisch", "Haltbares"],
        }
    )

    def fake_init(self, data_path=None, ingredients_df_path=None, pdf_paths=None):
        self.recipes = sample_recipes.copy()
        self.ingredients = sample_ingredients.copy()
        self.pdf_path = pdf_paths or "data/temp_pdfs"

    with patch.object(RecipeManager, "__init__", fake_init):
        manager = RecipeManager()
    return manager


class TestFilterRecipesByMealType:
    def setup_method(self):
        self.recipes_df = pd.DataFrame(
            {
                "id": ["r1", "r2", "r3", "r4"],
                "tags": [
                    "vegetarisch, lecker",
                    "vegan, gesund",
                    "protein, fleisch",
                    "alle, family",
                ],
            }
        )

    def test_filter_vegetarisch_includes_vegan(self):
        result = RecipeManager._filter_recipes_by_meal_type(self.recipes_df, "vegetarisch")
        assert len(result) == 2
        assert "r1" in result["id"].values
        assert "r2" in result["id"].values

    def test_filter_vegan_only(self):
        result = RecipeManager._filter_recipes_by_meal_type(self.recipes_df, "vegan")
        assert len(result) == 1
        assert "r2" in result["id"].values

    def test_filter_protein_excludes_vegetarisch_and_vegan(self):
        result = RecipeManager._filter_recipes_by_meal_type(self.recipes_df, "protein")
        assert "r1" not in result["id"].values
        assert "r2" not in result["id"].values
        assert "r3" in result["id"].values

    def test_filter_alle_returns_all(self):
        result = RecipeManager._filter_recipes_by_meal_type(self.recipes_df, "alle")
        assert len(result) == len(self.recipes_df)


class TestGetPdfTitleFromMealName:
    def test_removes_colon(self):
        assert RecipeManager.get_pdf_title_from_meal_name("Pasta: Deluxe") == "Pasta Deluxe"

    def test_removes_exclamation_mark(self):
        assert RecipeManager.get_pdf_title_from_meal_name("Soup!") == "Soup"

    def test_replaces_ampersand_with_und(self):
        assert RecipeManager.get_pdf_title_from_meal_name("Cheese & Bacon") == "Cheese und Bacon"

    def test_no_special_chars(self):
        assert RecipeManager.get_pdf_title_from_meal_name("Simple Recipe") == "Simple Recipe"

    def test_multiple_special_chars(self):
        result = RecipeManager.get_pdf_title_from_meal_name("Pasta: Tomato & Cheese!")
        assert result == "Pasta Tomato und Cheese"


class TestSumUpDuplicateIngredients:
    def test_sums_same_ingredient_and_unit(self):
        df = pd.DataFrame(
            [
                {"name": "Pasta", "unit": "g", "quantity": "200"},
                {"name": "Pasta", "unit": "g", "quantity": "100"},
            ]
        )
        result = RecipeManager._sum_up_duplicate_ingredients(df)
        assert len(result) == 1
        assert result[result["name"] == "Pasta"]["quantity"].values[0] == 300.0

    def test_keeps_different_units_separate(self):
        df = pd.DataFrame(
            [
                {"name": "Water", "unit": "ml", "quantity": "200"},
                {"name": "Water", "unit": "l", "quantity": "1"},
            ]
        )
        result = RecipeManager._sum_up_duplicate_ingredients(df)
        assert len(result) == 2

    def test_keeps_different_ingredients_separate(self):
        df = pd.DataFrame(
            [
                {"name": "Pasta", "unit": "g", "quantity": "200"},
                {"name": "Rice", "unit": "g", "quantity": "150"},
            ]
        )
        result = RecipeManager._sum_up_duplicate_ingredients(df)
        assert len(result) == 2


class TestFilterIngredients:
    def setup_method(self):
        self.df = pd.DataFrame(
            {
                "name": ["Pasta", "knoblauchzehe", "Tomaten", "Zwiebel", "Rucola"],
                "quantity": [200, 3, 150, 2, 50],
                "unit": ["g", "Stück", "g", "Stück", "g"],
            }
        )

    def test_filters_matching_ingredients(self):
        result = RecipeManager._filter_ingredients(self.df, ["knoblauch", "zwiebel"])
        assert "knoblauchzehe" not in result["name"].values
        assert "Zwiebel" not in result["name"].values

    def test_keeps_non_matching_ingredients(self):
        result = RecipeManager._filter_ingredients(self.df, ["knoblauch", "zwiebel"])
        assert "Pasta" in result["name"].values
        assert "Tomaten" in result["name"].values
        assert "Rucola" in result["name"].values

    def test_filter_is_case_insensitive(self):
        result = RecipeManager._filter_ingredients(self.df, ["PASTA"])
        assert "Pasta" not in result["name"].values

    def test_non_matching_filter_keeps_all(self):
        result = RecipeManager._filter_ingredients(self.df, ["nonexistent_ingredient_xyz"])
        assert len(result) == len(self.df)


class TestGenerateShoppingListText:
    def test_formats_ingredients_correctly(self):
        df = pd.DataFrame(
            {
                "name": ["Pasta", "Tomaten"],
                "quantity": [200.0, 3.0],
                "unit": ["g", "Stück"],
            }
        )
        result = RecipeManager._generate_ingredients_shopping_list_text(df)
        assert "Pasta" in result
        assert "Tomaten" in result
        assert "200" in result
        assert "\n" in result

    def test_returns_string(self):
        df = pd.DataFrame(
            {
                "name": ["Pasta"],
                "quantity": [200.0],
                "unit": ["g"],
            }
        )
        result = RecipeManager._generate_ingredients_shopping_list_text(df)
        assert isinstance(result, str)


class TestSampleFittingRecipes:
    def test_returns_correct_number_of_recipes(self, recipe_manager):
        user_settings = UserSettings(meal_type="alle", max_duration=120, cal_min=0)
        result = recipe_manager.sample_fitting_recipes(num_recipes=2, user_settings=user_settings)
        assert len(result) <= 2

    def test_uses_provided_recipes_dataframe(self, recipe_manager):
        user_settings = UserSettings(meal_type="alle", max_duration=120, cal_min=0)
        custom_df = pd.DataFrame(
            {
                "id": ["x1", "x2", "x3"],
                "title": ["Recipe A", "Recipe B", "Recipe C"],
                "tags": ["alle", "alle", "alle"],
                "total_time": [20, 30, 40],
                "calories": [500, 600, 700],
            }
        )
        result = recipe_manager.sample_fitting_recipes(num_recipes=2, user_settings=user_settings, recipes=custom_df)
        assert len(result) <= 2

    def test_returns_dataframe(self, recipe_manager):
        user_settings = UserSettings(meal_type="alle", max_duration=120, cal_min=0)
        result = recipe_manager.sample_fitting_recipes(num_recipes=3, user_settings=user_settings)
        assert isinstance(result, pd.DataFrame)

    def test_returns_all_when_fewer_than_requested(self, recipe_manager):
        user_settings = UserSettings(meal_type="alle", max_duration=120, cal_min=0)
        custom_df = pd.DataFrame(
            {
                "id": ["x1"],
                "title": ["Recipe A"],
                "tags": ["alle"],
                "total_time": [20],
                "calories": [500],
            }
        )
        result = recipe_manager.sample_fitting_recipes(num_recipes=5, user_settings=user_settings, recipes=custom_df)
        assert len(result) == 1


class TestGetRecipesFilteredByUserSettings:
    def test_filters_by_max_duration(self, recipe_manager):
        user_settings = UserSettings(meal_type="alle", max_duration=30, cal_min=0)
        result = recipe_manager.get_recipes_filtered_by_user_settings(user_settings)
        assert all(result["total_time"] <= 30)

    def test_filters_by_cal_min(self, recipe_manager):
        user_settings = UserSettings(meal_type="alle", max_duration=120, cal_min=600)
        result = recipe_manager.get_recipes_filtered_by_user_settings(user_settings)
        assert all(result["calories"] >= 600)

    def test_filters_by_meal_type_vegan(self, recipe_manager):
        user_settings = UserSettings(meal_type="vegan", max_duration=120, cal_min=0)
        result = recipe_manager.get_recipes_filtered_by_user_settings(user_settings)
        assert all("vegan" in tags.lower() for tags in result["tags"])


class TestGetRecipesById:
    def test_returns_matching_recipes(self, recipe_manager):
        result = recipe_manager.get_recipes_by_id(["r1", "r3"])
        assert set(result["id"].tolist()) == {"r1", "r3"}

    def test_returns_empty_for_no_match(self, recipe_manager):
        result = recipe_manager.get_recipes_by_id(["nonexistent"])
        assert len(result) == 0

    def test_returns_dataframe(self, recipe_manager):
        result = recipe_manager.get_recipes_by_id(["r1"])
        assert isinstance(result, pd.DataFrame)


class TestGetRecipeTitlesById:
    def test_returns_titles_for_ids(self, recipe_manager):
        result = recipe_manager.get_recipe_titles_by_id(["r1", "r2"])
        assert "Pasta Primavera" in result
        assert "Veggie Burger" in result

    def test_returns_empty_list_for_no_match(self, recipe_manager):
        result = recipe_manager.get_recipe_titles_by_id(["nonexistent"])
        assert result == []

    def test_returns_list(self, recipe_manager):
        result = recipe_manager.get_recipe_titles_by_id(["r1"])
        assert isinstance(result, list)
