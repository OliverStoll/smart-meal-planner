from time import sleep
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By

from logs.logs import create_logger
from settings import RECIPE_URL
from data_ingestion.utils import scroll_driver_down
from database.engine import df_from_sql, df_to_sql
from web.driver import create_driver


class HelloFreshLinkCrawler:
    log = create_logger("HelloFreshLinkCrawler")

    def assure_recipe_links(self, use_stored: bool, save_to_db: bool = False) -> pd.DataFrame:
        if use_stored:
            try:
                return self.get_recipes_from_db()
            except Exception as e:
                self.log.warning(f"Could not load recipe links from database: {e}")
        recipe_links = self.get_all_recipe_links()
        self.log.info(f"Found {len(recipe_links)} unique recipe links")
        if save_to_db:
            df_to_sql(ref="links", df=recipe_links)
        return recipe_links

    def get_recipes_from_db(self) -> pd.DataFrame:
        recipe_links = df_from_sql(ref="links")
        assert len(recipe_links) > 0, "No recipe links found in the database."
        self.log.info(f"Loaded {len(recipe_links)} Recipe links")
        return recipe_links

    def get_all_recipe_links(self) -> pd.DataFrame:
        """
        Scrape all individual recipe links from all categories and filter out duplicates.

        Returns:
            List of recipe data dictionaries containing recipe links and category paths.
        """
        driver = create_driver()
        category_paths = self.get_recipe_category_paths()
        self.log.info(f"Found {len(category_paths)} categories")
        all_categories_link_data = []
        for idx, category_path in enumerate(category_paths, start=1):
            category_recipe_links = self.get_recipes_links_of_category(driver=driver, category_path=category_path)
            self.log.debug(
                f"[{idx}/{len(category_paths)}]  Found {len(category_recipe_links)} recipes in category {category_path}"
            )
            category_link_data = []
            for recipe_link in category_recipe_links:
                recipe_data = {
                    "link": recipe_link,
                    "category": category_path,
                    "id": recipe_link.split("-")[-1],
                }
                category_link_data.append(recipe_data)
            all_categories_link_data.extend(category_link_data)

        driver.close()
        recipes_links = pd.DataFrame(all_categories_link_data)
        recipes_links = recipes_links.dropna()
        recipes_links = recipes_links.drop_duplicates(subset=["link"])
        recipes_links = recipes_links.drop_duplicates(subset=["id"])
        recipes_links["category_friendly"] = (
            recipes_links["category"].str.replace("rezepte-", "").replace("-rezepte", "")
        )
        return recipes_links

    def get_recipe_category_paths(self) -> list[str]:
        """
        Get all recipe categories from the HelloFresh website.

        Returns:
            List of recipe category paths.
        """
        driver = create_driver()
        driver.get(RECIPE_URL)
        category_link_elements = driver.find_elements(By.CSS_SELECTOR, "a")
        category_links = [category.get_attribute("href") for category in category_link_elements]
        category_paths = self._clean_recipe_category_paths(category_links)
        driver.close()
        return category_paths

    @staticmethod
    def _clean_recipe_category_paths(category_links: list[str]) -> list[str]:
        """
        Clean and extract category paths from the list of category links.

        Filters out non-relevant links that contain no recipe IDs (e.g., 65d4898f6c4f22398987607a)
         or are not from the base link.

        Args:
            category_links: List of category links.

        Returns:
            List of cleaned category paths.
        """
        category_links = list(set(category_links))  # only keep unique links
        filtered_links = [link for link in category_links if RECIPE_URL in link]
        filtered_links = [link.split("&")[0] for link in filtered_links]
        filtered_links = [link for link in filtered_links if len(link.split("-")[-1]) != 24]
        category_paths = [link.split("/")[-1] for link in filtered_links]
        return category_paths

    def get_recipes_links_of_category(
        self,
        driver: webdriver.Chrome,
        category_path: str,
        link_selector: str = 'div[data-test-id="recipe-image-card"] > a',
        load_timer: int = 2,
    ):
        """
        Get all recipe links from a category page.

        Args:
            category_path: Category path to scrape.
            link_selector: CSS selector for recipe links.
            load_timer: Time to wait for the page to load.
        """
        link = f"{RECIPE_URL}/{category_path}?page=999"
        driver.get(link)
        sleep(load_timer)
        scroll_driver_down(driver=driver)
        recipe_links = driver.find_elements(By.CSS_SELECTOR, link_selector)
        recipe_links_href = self._clean_recipe_links(recipe_links)
        return recipe_links_href

    @staticmethod
    def _clean_recipe_links(
        recipe_link_elements: list[webdriver.remote.webelement.WebElement],
    ):
        recipe_links_href = [recipe_link.get_attribute("href") for recipe_link in recipe_link_elements]
        recipe_links_href = [link for link in recipe_links_href if len(link.split("-")[-1]) == 24]
        recipe_links_href = list(set(recipe_links_href))
        return recipe_links_href


if __name__ == "__main__":
    crawler = HelloFreshLinkCrawler()
    recipe_links = crawler.assure_recipe_links(use_stored=False, save_to_db=True)
    print(recipe_links)
