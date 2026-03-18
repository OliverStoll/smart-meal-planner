import ast
import os
from pathlib import Path

import pandas as pd
import pytest

# Set DOCKER_WORKDIR so common_utils can resolve the project ROOT_DIR
os.environ.setdefault("DOCKER_WORKDIR", str(Path(__file__).parent.parent))


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
def recipe_links():
    return pd.read_csv("tests/fixtures/recipe_links.csv")


@pytest.fixture
def raw_recipes():
    return pd.read_csv("tests/fixtures/recipes_raw.csv")


@pytest.fixture
def cleaned_recipes():
    df = pd.read_csv("tests/fixtures/recipes_cleaned.csv")
    for column in ["ingredients", "instructions", "instruction_images"]:
        df[column] = df[column].apply(ast.literal_eval)
    return df
