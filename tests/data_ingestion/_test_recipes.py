import os
from unittest.mock import patch
import pandas as pd

from data_ingestion.crawler.links import HelloFreshLinkCrawler
from data_ingestion.crawler.recipes import HelloFreshRecipeCrawler
from web.driver import create_driver


class TestHelloFreshScraper:
    expected_recipes_columns = {
        "link",
        "category",
        "id",
        "category_friendly",
        "title",
        "description",
        "tags",
        "hero_image",
        "ingredients",
        "instructions",
        "pdf",
    }

    def test_get_all_recipes(self, recipe_links):
        with patch.object(
            HelloFreshLinkCrawler, "assure_recipe_links", return_value=recipe_links
        ):
            crawler = HelloFreshRecipeCrawler()
            crawler.num_threads = 1
            recipes = crawler.get_all_recipes(use_stored_links=True, save_to_db=False)
        assert isinstance(recipes, pd.DataFrame), "Expected a DataFrame of recipes"
        assert len(recipes) == len(
            recipe_links
        ), "Expected the number of recipes to match the number of recipe links"

        assert self.expected_recipes_columns.issubset(
            set(recipes.columns)
        ), f"Expected columns {self.expected_recipes_columns} in the recipes"

    def test_get_all_recipes_details(self, recipe_links):
        output_file = ".temp_test.csv"
        os.remove(output_file) if os.path.exists(output_file) else None
        driver = create_driver()
        recipes_details = HelloFreshRecipeCrawler().get_all_recipes_details(
            recipe_links, save_path=output_file, driver=driver
        )
        assert isinstance(
            recipes_details, pd.DataFrame
        ), "Expected a DataFrame of recipe details"
        assert len(recipes_details) == len(
            recipe_links
        ), "Expected the number of recipe details to match the number of recipe links"
        assert self.expected_recipes_columns.issubset(
            set(recipes_details.columns)
        ), f"Expected columns {self.expected_recipes_columns} in the recipe details"
        assert os.path.exists(
            output_file
        ), f"Expected the recipe details to be saved to f{output_file}"
        os.remove(output_file)
