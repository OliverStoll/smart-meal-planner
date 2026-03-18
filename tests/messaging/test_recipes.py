import pytest

from messaging.callbacks.settings_types import UserSettings
from messaging.recipes import (
    filtered_recipes,
    num_filtered_recipes,
    sample_recipes,
    recipe_titles_by_id,
)


@pytest.fixture
def user_settings():
    return UserSettings()


def test_filtered_recipes(user_settings, cleaned_recipes):
    recipes = filtered_recipes(user_settings, recipes=cleaned_recipes)
    assert len(recipes) == len(cleaned_recipes), "No filtering should occur with default user settings"


def test_num_of_filtered_recipes(user_settings, cleaned_recipes):
    assert len(cleaned_recipes) == num_filtered_recipes(user_settings=user_settings, recipes=cleaned_recipes)


def test_sample_recipes(user_settings, cleaned_recipes):
    num_samples = 2
    samples = sample_recipes(num_recipes=num_samples, user_settings=user_settings, recipes=cleaned_recipes)
    assert len(samples) == num_samples, "Sampling fn should sample given amount"


def test_recipe_titles_by_id(cleaned_recipes):
    titles = recipe_titles_by_id(recipes=cleaned_recipes, recipe_ids=[cleaned_recipes["id"][0]])
    assert titles == ["Gebackener Camembert mit Honig"]
