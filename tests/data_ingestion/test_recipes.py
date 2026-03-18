from unittest.mock import patch
import pandas as pd
import pytest

from data_ingestion.crawler.links import HelloFreshLinkCrawler
from data_ingestion.crawler.recipes import (
    HelloFreshRecipeCrawler,
    clean_ingredient_text,
)
from web.driver import create_driver


@pytest.mark.slow
class TestHelloFreshScraper:
    expected_recipes_columns = {
        "link",
        "category",
        "id",
        "category_friendly",
        "title",
        "description",
        # "tags",  # TODO
        "hero_image",
        "ingredients",
        "instructions",
        "pdf",
    }

    def test_get_all_recipes(self, recipe_links):
        with patch.object(HelloFreshLinkCrawler, "assure_recipe_links", return_value=recipe_links):
            crawler = HelloFreshRecipeCrawler()
            crawler.num_threads = 1
            recipes = crawler.get_all_recipes(use_stored_links=True, save_to_db=False)
        assert isinstance(recipes, pd.DataFrame), "Expected a DataFrame of recipes"
        assert len(recipes) == len(recipe_links), "Expected the number of recipes to match the number of recipe links"
        assert self.expected_recipes_columns.issubset(
            set(recipes.columns)
        ), f"Expected columns {self.expected_recipes_columns} in the recipes"

    def test_get_all_recipes_details(self, recipe_links):
        driver = create_driver()
        recipes_details = HelloFreshRecipeCrawler().get_all_recipes_details(recipe_links, driver=driver)
        assert isinstance(recipes_details, pd.DataFrame), "Expected a DataFrame of recipe details"
        assert len(recipes_details) == len(
            recipe_links
        ), "Expected the number of recipe details to match the number of recipe links"
        assert self.expected_recipes_columns.issubset(
            set(recipes_details.columns)
        ), f"Expected columns {self.expected_recipes_columns} in the recipe details"
        driver.close()


@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("2 kg\nKartoffeln", {"quantity": 2, "unit": "kg", "name": "Kartoffeln"}),
        ("5\nÄpfel", {"quantity": 5, "unit": "", "name": "Äpfel"}),
        ("Stück\nZitrone", {"quantity": 1, "unit": "Stück", "name": "Zitrone"}),
        ("1.5 EL\nZucker", {"quantity": 1.5, "unit": "EL", "name": "Zucker"}),
        ("invalid", None),
        ("too\nmany\nlines", None),
    ],
)
def test_clean_ingredient_text(input_text, expected):
    assert clean_ingredient_text(input_text) == expected
