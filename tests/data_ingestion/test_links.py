from unittest.mock import patch
import pandas as pd
import pytest

from data_ingestion.crawler.links import HelloFreshLinkCrawler
from web.driver import create_driver


@pytest.mark.slow
class TestHelloFreshLinkCrawler:
    crawler = HelloFreshLinkCrawler()

    def test_get_recipe_category_paths(self):
        category_paths = self.crawler.get_recipe_category_paths()
        assert isinstance(category_paths, list), "Expected a list of category paths"
        assert len(category_paths) > 50, "Expected at least 50 category paths"

    def test_get_recipe_links_of_category(self, category_path):
        driver = create_driver()
        links = self.crawler.get_recipes_links_of_category(driver=driver, category_path=category_path)
        driver.close()
        assert isinstance(links, list), "Expected a list of links"
        assert len(links) > 10, "Expected at least 10 links in the category"

    def test_get_all_recipes_links(self, category_paths):
        with patch.object(
            HelloFreshLinkCrawler,
            attribute="get_recipe_category_paths",
            return_value=category_paths,
        ):
            recipes_links = self.crawler.get_all_recipe_links()
        assert isinstance(recipes_links, pd.DataFrame), "Expected a DataFrame of recipe links"
        assert len(recipes_links) > 50, "Expected at least 50 recipe links"
        assert "link" in recipes_links.columns, "Expected 'link' column in the DataFrame"
        assert "category" in recipes_links.columns, "Expected 'category' column in the DataFrame"
        assert "id" in recipes_links.columns, "Expected 'id' column in the DataFrame"

    def test_assure_recipe_links_from_db(self, single_category_path):
        with patch.object(
            HelloFreshLinkCrawler,
            attribute="get_recipe_category_paths",
            return_value=single_category_path,
        ):
            recipe_links = self.crawler.assure_recipe_links(use_stored=True, save_to_db=False)
        assert isinstance(recipe_links, pd.DataFrame), "Expected a DataFrame of recipe links from the database"
        assert len(recipe_links) > 10, "Expected at least 10 recipe links in the database"
        assert "link" in recipe_links.columns, "Expected 'link' column"

    def test_assure_recipe_links_crawled(self, single_category_path):
        with patch.object(
            HelloFreshLinkCrawler,
            attribute="get_recipes_from_db",
            side_effect=Exception("DB error"),
        ):
            with patch.object(
                HelloFreshLinkCrawler,
                "get_recipe_category_paths",
                return_value=single_category_path,
            ):
                assured_links = self.crawler.assure_recipe_links(use_stored=True, save_to_db=False)
        assert isinstance(assured_links, pd.DataFrame), "Expected a DataFrame of assured recipe links"
        assert len(assured_links) > 20, "Expected at least 20 recipe links"
