import pandas as pd
from logs.logs import create_logger

from database.engine import recipes_from_sql
from src.messaging.callbacks.settings_types import UserSettings

log = create_logger("Recipe Messager")


def sample_recipes(num_recipes: int, user_settings: UserSettings, recipes: pd.DataFrame = None) -> pd.DataFrame:
    """
    Filters the recipes based on user settings and returns a DataFrame of selected recipes.

    Args:
        num_recipes: The number of recipes to return.
        user_settings: The user settings containing meal type, max duration, and min calories.
        recipes: Optional; if provided, it will be used instead of the default recipes DataFrame.

    Returns:
        A DataFrame containing the filtered recipes.
    """
    if recipes is None:
        recipes = filtered_recipes(user_settings=user_settings)
    if recipes is not None and num_recipes < len(recipes):
        recipes = recipes.sample(num_recipes)
        recipes.reset_index(drop=True, inplace=True)
    return recipes


def num_filtered_recipes(user_settings: UserSettings, recipes: pd.DataFrame | None = None) -> int:
    """Filter the recipes based on user settings and returns the number of selected recipes."""
    recipes_df = filtered_recipes(user_settings=user_settings, recipes=recipes)
    return len(recipes_df) if recipes_df is not None else 0


def filtered_recipes(user_settings: UserSettings, recipes: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Filters the recipes based on user settings and returns the number of selected recipes.

    Args:
        user_settings: The user settings containing meal type, max duration, and min calories.
        recipes: Optional; if provided, will be used instead of the default DataFrame of all recipes.

    Returns:
        An integer representing the number of filtered recipes.
    """
    if recipes is None:
        recipes = recipes_from_sql()
    # recipes = recipes[recipes["total_time"] <= user_settings.max_duration]  # TODO
    # recipes = recipes[recipes["calories"] >= user_settings.cal_min]
    recipes = filter_recipes_by_meal_type(recipes=recipes, meal_type=user_settings.meal_type)
    return recipes


def filter_recipes_by_meal_type(recipes: pd.DataFrame, meal_type: str) -> pd.DataFrame:
    if meal_type == "vegetarisch":
        tags = ["vegetarisch", "vegan"]
        recipes = recipes[recipes["tags"].apply(lambda x: any(tag in x.lower() for tag in tags))]
    elif meal_type == "vegan":
        tags = ["vegan"]
        recipes = recipes[recipes["tags"].apply(lambda x: any(tag in x.lower() for tag in tags))]
    elif meal_type == "protein":
        negativ_tags = ["vegetarisch", "vegan"]
        recipes = recipes[recipes["tags"].apply(lambda x: not any(tag in x for tag in negativ_tags))]
    return recipes


def recipes_by_id(recipes: pd.DataFrame, recipe_ids: list[str]) -> pd.DataFrame:
    recipes_df = recipes[recipes["id"].isin(recipe_ids)]
    return recipes_df


def recipe_titles_by_id(recipes: pd.DataFrame, recipe_ids: list[str]) -> list[str]:
    recipes_df = recipes_by_id(recipes=recipes, recipe_ids=recipe_ids)
    return recipes_df["title"].tolist()
