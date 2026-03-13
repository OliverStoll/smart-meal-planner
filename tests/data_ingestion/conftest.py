import pandas as pd
import pytest

from config.settings import ROOT_DIR


@pytest.fixture
def category_path():
    return "amerikanische-rezepte"


@pytest.fixture
def category_paths():
    return ["amerikanische-rezepte", "fusions-rezepte"]


@pytest.fixture
def single_category_path():
    return ["fusions-rezepte"]


@pytest.fixture
def recipe_links_df():
    return pd.read_csv(ROOT_DIR / "tests/fixtures/recipe_links.csv")


@pytest.fixture
def raw_recipes_df():
    return pd.read_csv(ROOT_DIR / "tests/fixtures/raw_recipes.csv")
