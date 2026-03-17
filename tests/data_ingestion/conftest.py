import pytest


@pytest.fixture
def category_path():
    return "amerikanische-rezepte"


@pytest.fixture
def category_paths():
    return ["amerikanische-rezepte", "fusions-rezepte"]


@pytest.fixture
def single_category_path():
    return ["fusions-rezepte"]
