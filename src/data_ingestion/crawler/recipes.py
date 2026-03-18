import os
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
from time import sleep
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.ie.webdriver import WebDriver

from logs.logs import create_logger
from database import RAW_RECIPES_REF
from data_ingestion.crawler.links import HelloFreshLinkCrawler
from database.engine import df_to_sql
from messaging.utils import str_to_int
from web.driver import create_driver


def clean_ingredient_text(ingredient_item_text) -> dict | None:
    ingredient_item_lines = ingredient_item_text.split("\n")
    if len(ingredient_item_lines) != 2:
        return None
    amount_line, name_line = ingredient_item_lines
    amount_tokens = amount_line.split(" ")
    if len(amount_tokens) == 1 and amount_tokens[0].isdigit():
        quantity = amount_tokens[0]
        unit = ""
    elif len(amount_tokens) == 1 and amount_tokens[0] == "Stück":
        unit = amount_tokens[0]
        quantity = 1
    elif len(amount_tokens) >= 2:
        quantity, unit = amount_tokens[0], amount_tokens[1]
    else:
        quantity, unit = 0, ""
    quantity = str_to_int(quantity)
    if isinstance(quantity, str):
        try:
            quantity = float(quantity)
        except ValueError:
            pass
    return {"quantity": quantity, "unit": unit, "name": name_line}


class HelloFreshRecipeCrawler:
    log = create_logger("HelloFreshScraper")
    base_link = "https://www.hellofresh.de/recipes/"
    thread_output_path = "data/temp_data/.temp"
    num_threads = 5

    def __init__(self):
        self.link_crawler = HelloFreshLinkCrawler()
        self.crawling_config = {
            "title": {
                "selector": 'div[data-test-id="recipe-description"] h1',
            },
            "description": {
                "selector": 'div[data-test-id="recipe-description"] > div:nth-child(8)',
            },
            "tags": {
                "selector": 'div[data-test-id="recipe-description"] > div:nth-child(5)',
                "postprocessing_fn": self._process_tags,
            },
            "hero_image": {
                "selector": 'div[data-test-id="recipe-hero-image"] img',
                "postprocessing_fn": self._process_hero_image,
            },
            "ingredients": {
                "selector": 'div[data-test-id="ingredients-list"]',
                "postprocessing_fn": self._get_ingredients,
            },
            "nutrients": {
                "selector": 'div[data-test-id="nutritions"]',
                "postprocessing_fn": self._get_nutrients,
            },
            "instructions": {
                "selector": 'div[data-test-id="instructions"]',
                "postprocessing_fn": self._get_instructions,
            },
            "pdf": {
                "selector": 'div[data-test-id="instructions"] a',
                "postprocessing_fn": self._process_pdf,
            },
        }
        os.makedirs(self.thread_output_path, exist_ok=True)

    def get_all_recipes(self, use_stored_links: bool, save_to_db: bool = True) -> pd.DataFrame:
        """
        Scrape all recipes from all categories and save them to a csv file.

        Args:
            save_to_db: If True, save the recipes to a csv file.
            use_stored_links: If True, use the stored recipe links from the csv file.

        Returns:
            DataFrame containing all recipes details.
        """
        os.makedirs(self.thread_output_path, exist_ok=True)
        all_recipe_links = self.link_crawler.assure_recipe_links(use_stored=use_stored_links, save_to_db=True)
        recipe_links_split = np.array_split(all_recipe_links, self.num_threads)

        with ThreadPoolExecutor() as executor:
            futures = []
            thread_drivers = []
            for thread_id, thread_recipe_links in enumerate(recipe_links_split, start=1):
                driver = create_driver()
                thread_recipe_links = pd.DataFrame(thread_recipe_links, columns=all_recipe_links.columns)
                future = executor.submit(self.get_all_recipes_details, thread_recipe_links, driver)
                futures.append(future)
                thread_drivers.append(driver)

        all_recipes_details: list[pd.DataFrame] = [future.result() for future in futures]
        for driver in thread_drivers:
            driver.close()
        recipes_details = pd.concat(all_recipes_details, ignore_index=True)
        if save_to_db:
            df_to_sql(ref=RAW_RECIPES_REF, df=recipes_details)
        return recipes_details

    def get_all_recipes_details(self, recipe_link_entries: pd.DataFrame, driver: WebDriver) -> pd.DataFrame:
        """
        Scrape all recipes from a list of recipe links.

        Args:
            recipe_link_entries: List of recipe dictionaries including links to scrape.
            driver: Selenium WebDriver instance to use for scraping.

        Returns:
            DataFrame containing all recipies details.
        """
        all_recipes_details = []
        for idx, recipe_data in enumerate(recipe_link_entries.to_dict(orient="records"), start=1):
            try:
                recipe_values = self.get_recipe_details(recipe_data, driver)
                self.log.debug(f"[{idx:3>}] {recipe_values['title']} - {recipe_values}")
                all_recipes_details.append(recipe_values)
            except Exception as e:
                self.log.error(f"Error in getting details from {recipe_data['link']}: {e}")
        all_recipes_details = pd.DataFrame(all_recipes_details)
        return all_recipes_details

    def get_recipe_details(self, recipe_data_row: dict[str, str | None], driver: WebDriver) -> dict:
        driver.get(recipe_data_row["link"])
        for attribute_name, attribute_crawl_config in self.crawling_config.items():
            try:
                attribute_data = self.get_recipe_attribute_value(
                    attribute_name=attribute_name,
                    config=attribute_crawl_config,
                    driver=driver,
                )
                recipe_data_row.update(attribute_data)
            except Exception as e:
                msg = str(e).split("\n")[0]
                self.log.debug(f"Missing {attribute_name}: {str(msg)}")
                recipe_data_row[attribute_name] = None
        return recipe_data_row

    def get_recipe_attribute_value(self, attribute_name: str, config: dict, driver: WebDriver) -> dict:
        """
        Get a single recipe detail value using the provided getter function.

        Arguments:
            attribute_name: Name of the recipe detail to get.
            config: Details to get the recipe detail value.
        """
        detail_element = driver.find_element(by=By.CSS_SELECTOR, value=config["selector"])
        if "postprocessing_fn" in config:
            return config["postprocessing_fn"](detail_element)
        else:
            return {attribute_name: detail_element.text}

    def _process_hero_image(self, element):
        hero_image_link = element.get_attribute("src")
        return {"hero_image": hero_image_link.split(" ")[0]}

    def _process_tags(self, element):
        tags_text = element.text
        result = {}
        parts = tags_text.split("\\n: \\n")
        for i in range(len(parts) - 1):
            key = parts[i].split("\\n")[-1].strip()
            value = parts[i + 1].split("\\n")[0].strip()
            result[key] = value
        return result
        # return {"tags": tags_list}

    def _get_ingredients(self, element):
        ingredients_data = {"ingredients": []}
        button_selector = 'div[aria-label="Segmented Button"] > button[title="2"]'
        try:
            element.find_element(By.CSS_SELECTOR, button_selector).click()
            sleep(0.3)
        except Exception:
            self.log.warning("Meals: 2 button not found")
        selector = 'div[data-test-id="ingredient-item-shipped"]'
        ingredient_items = element.find_elements(By.CSS_SELECTOR, selector)
        for ingredient_item in ingredient_items:
            ingredient_item_data = clean_ingredient_text(ingredient_item.text)
            if ingredient_item_data:
                ingredients_data["ingredients"].append(ingredient_item_data)
        return ingredients_data

    def _get_nutrients(self, element):
        nutrient_lines = element.text.replace(" kcal", "").replace(" g", "").split("\n")
        return {
            "calories": nutrient_lines[6],
            "fat": nutrient_lines[8],
            "saturated_fat": nutrient_lines[10],
            "carbs": nutrient_lines[12],
            "sugar": nutrient_lines[14],
            "protein": nutrient_lines[16],
            "salt": nutrient_lines[18],
        }

    def _get_instructions(self, element):
        instructions_steps = element.find_elements(By.CSS_SELECTOR, 'div[data-test-id="instruction-step"]')
        instructions_text = [instruction_step.text for instruction_step in instructions_steps]
        instruction_image_links = []
        for instruction_step in instructions_steps:
            try:
                instruction_image_links.append(
                    instruction_step.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
                )
            except NoSuchElementException:
                instruction_image_links.append(None)

        return {
            "instructions": instructions_text,
            "instruction_images": instruction_image_links,
        }

    @staticmethod
    def _process_pdf(element):
        return {"pdf": element.get_attribute("href")}


if __name__ == "__main__":
    scraper = HelloFreshRecipeCrawler()
    scraper.get_all_recipes(use_stored_links=True, save_to_db=True)
