import json
import os
from time import sleep
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
import pandas as pd
from selenium.webdriver.ie.webdriver import WebDriver

from utils.config import create_logger, ROOT_DIR


class HelloFreshScraper:
    log = create_logger('HelloFreshScraper')
    base_link = "https://www.hellofresh.de/recipes/"
    output_path = f'{ROOT_DIR}/data/temp_data'
    recipe_links_path = f'{output_path}/links.csv'

    def __init__(self):
        self.driver = webdriver.Chrome()
        self.recipe_details_scraping_data = {
            'description': {
                'selector': 'div[data-test-id="recipe-description"]',
                'getter_function': self._get_description,
            },
            'times': {
                'selector': 'div[data-test-id="recipe-description"]',
                'getter_function': self._get_times,
            },
            'ingredients': {
                'selector': 'div[data-test-id="ingredients-list"]',
                'getter_function': self._get_ingredients,
            },
            'nutrients': {
                'selector': 'div[data-test-id="nutritions"]',
                'getter_function': self._get_nutrients,
            },
            'instructions': {
                'selector': 'div[data-test-id="instructions"]',
                'getter_function': self._get_instructions,
            },
            'pdf': {
                'selector': 'div[data-test-id="instructions"]',
                'getter_function': self._get_pdf,
            }
        }
        os.makedirs(self.output_path, exist_ok=True)

    def get_all_recipes(self, use_stored_links: bool, save_results: bool = True) -> pd.DataFrame:
        """
        Scrape all recipes from all categories and save them to a csv file.

        Args:
            save_results: If True, save the recipes to a csv file.
            use_stored_links: If True, use the stored recipe links from the csv file.

        Returns:
            DataFrame containing all recipes details.
        """
        all_recipe_link_entires = self.load_or_get_recipe_links(
            use_stored_links=use_stored_links, save_results=save_results
        )

        recipes_df = self.get_all_recipes_details(recipe_link_entries=all_recipe_link_entires)
        self.log.info(f"Length raw: {len(recipes_df)}")
        cleaned_df = self.clean_recipes_df(recipes_df)
        self.log.info(f"Length cleaned: {len(cleaned_df)}")

        if save_results:
            recipes_df.to_csv(f'{self.output_path}/recipes.csv', index=False)
            cleaned_df.to_csv(f'{self.output_path}/cleaned.csv', index=False)
            self.log.info("Recipes saved to csv")

        return cleaned_df

    def load_or_get_recipe_links(self, use_stored_links: bool, save_results: bool = True) -> pd.DataFrame:
        if use_stored_links:
            recipe_links_df = pd.read_csv(self.recipe_links_path)
            self.log.info(f"Loaded {len(recipe_links_df)} Recipe links")
            return recipe_links_df

        category_paths = self._get_recipe_category_paths()
        self.log.info(f"Found {len(category_paths)} categories")

        recipes_df = self.get_all_recipe_links(category_paths=category_paths)

        if save_results:
            recipes_df.to_csv(self.recipe_links_path, index=False)
            self.log.info(f"{len(recipes_df)} Recipe links saved to {self.recipe_links_path}")

        return recipes_df

    def get_all_recipe_links(self, category_paths: list[str]) -> pd.DataFrame:
        """
        Scrape all individual recipe links from all categories, and filter out duplicates.

        Args:
            category_paths: List of category link paths to scrape.

        Returns:
            List of recipe data dictionaries containing recipe links and category paths.
        """
        all_recipe_data = []
        for idx, category_path in enumerate(category_paths, start=1):
            category_recipe_links = self.get_recipes_links_of_category(category_path=category_path)
            self.log.info(
                f"[{idx}/{len(category_paths)}]  Found {len(category_recipe_links)} recipes in category {category_path}"
            )
            category_recipe_data = []
            for recipe_link in category_recipe_links:
                recipe_data = {'link': recipe_link, 'category': category_path, 'id': recipe_link.split('-')[-1]}
                category_recipe_data.append(recipe_data)

            all_recipe_data.extend(category_recipe_data)

        recipes_df = pd.DataFrame(all_recipe_data)
        recipes_df = recipes_df.dropna()
        recipes_df = recipes_df.drop_duplicates(subset=['link'])
        recipes_df = recipes_df.drop_duplicates(subset=['id'])
        recipes_df['category_friendly'] = recipes_df['category'].str.replace('e-rezepte', '').replace('-rezepte', '')
        return recipes_df

    def get_recipes_links_of_category(
            self,
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
        link = f"{self.base_link}/{category_path}?page=999"
        self.driver.get(link)
        sleep(load_timer)
        self._scroll_driver_down(driver=self.driver)
        recipe_links = self.driver.find_elements(By.CSS_SELECTOR, link_selector)
        recipe_links_href = self._clean_recipe_links(recipe_links)
        return recipe_links_href

    def get_all_recipes_details(
            self,
            recipe_link_entries: pd.DataFrame,
            driver: WebDriver | None = None
    ) -> pd.DataFrame:
        """
        Scrape all recipes from a list of recipe links.

        Args:
            recipe_link_entries: List of recipe dictionaries including links to scrape.
            driver: Selenium WebDriver instance to use for scraping.

        Returns:
            DataFrame containing all recipes details.
        """
        if driver is None:
            driver = self.driver
        all_recipes_details = []
        for idx, recipe_data in enumerate(recipe_link_entries.to_dict(orient='records'), start=1):
            try:
                recipe_values = self.get_single_recipe_details(recipe_data, driver)
                self.log.debug(f"[{idx:3>}] {recipe_values['title']}")
                all_recipes_details.append(recipe_values)
            except Exception as e:
                self.log.error(f"Error in getting details from {recipe_data['link']}: {e}")

        recipes_df = pd.DataFrame(all_recipes_details)
        return recipes_df

    def get_single_recipe_details(self, recipe_data_entry: dict[str, str], driver: WebDriver) -> dict:
        """
        Scrape details of a single recipe from its link.
        """
        driver.get(recipe_data_entry['link'])
        for detail_name, detail_scraping_data in self.recipe_details_scraping_data.items():
            try:
                detail_values = self.get_single_recipe_detail_value(
                    detail_scraping_data=detail_scraping_data,
                    recipe_detail_link=recipe_data_entry['link'],
                    driver=driver,
                )
            except Exception as e:
                self.log.warning(f"Error in getting {detail_name} from {recipe_data_entry['link']}: {e}")
                detail_values = {}

            recipe_data_entry.update(detail_values)
        return recipe_data_entry

    def get_single_recipe_detail_value(
            self,
            detail_scraping_data: dict,
            recipe_detail_link: str,
            driver: WebDriver,
    ) -> dict:
        """
        Get a single recipe detail value using the provided getter function.

        If the element is not found, log a warning and return an empty dictionary.

        Args:
            detail_scraping_data: Function to get the recipe detail value.
            recipe_detail_link: Link to the recipe detail page.

        """
        detail_selector = detail_scraping_data['selector']
        detail_getter_function = detail_scraping_data['getter_function']
        detail_element = driver.find_element(by=By.CSS_SELECTOR, value=detail_selector)
        try:
            detail_values = detail_getter_function(detail_element)  # noqa
        except NoSuchElementException:
            getter_name = detail_scraping_data.__name__.replace('_get_', '').upper()
            self.log.warn(f"{getter_name} not found: {recipe_detail_link}")
            detail_values = {}
        except Exception as e:
            self.log.warn(f"Error in {detail_scraping_data.__name__}: {recipe_detail_link} - {e}")
            detail_values = {}

        return detail_values

    @staticmethod
    def clean_recipes_df(recipes_df):
        """
        Clean the recipes DataFrame by dropping NaN values and duplicates.
        """
        cleaned_df = recipes_df.dropna()
        cleaned_df = cleaned_df.drop_duplicates(subset=['pdf_link'])
        return cleaned_df

    """
    Protected methods
    """

    @staticmethod
    def _scroll_driver_down(driver: WebDriver):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    @staticmethod
    def _clean_recipe_links(recipe_link_elements: list[webdriver.remote.webelement.WebElement]):
        recipe_links_href = [recipe_link.get_attribute('href') for recipe_link in recipe_link_elements]
        recipe_links_href = [link for link in recipe_links_href if len(link.split('-')[-1]) == 24]
        recipe_links_href = list(set(recipe_links_href))  # only keep unique links
        return recipe_links_href

    def _get_description(self, description_element):
        title = description_element.find_element(By.CSS_SELECTOR, 'h1').text
        description_selector = 'div:nth-child(2) > div:nth-child(2) > div:nth-child(1)'
        description_div = description_element.find_element(By.CSS_SELECTOR, description_selector)
        description_tags = description_div.text.split('\n')[1].replace('Tags:', '').split('•')
        description_values = {'title': title, 'description': description_div.text, 'tags': description_tags}
        return description_values

    def _get_times(self, description_element):
        selector = 'div:nth-child(2) > div:nth-child(2) > div:nth-child(2)'
        times_div = description_element.find_element(By.CSS_SELECTOR, selector)
        times_lines = times_div.text.replace(' Minuten', '').split('\n')
        times_values = {'total_time': times_lines[1]}
        try:
            times_values['preparation_time'] = times_lines[3]
            times_values['cooking_time'] = times_lines[5]
        except Exception:
            pass
        return times_values

    def _get_ingredients(self, ingredients_element):
        selector = 'div[data-test-id="ingredient-item-shipped"]'
        ingredient_items = ingredients_element.find_elements(By.CSS_SELECTOR, selector)
        ingredients_data = {'ingredients': []}
        for ingredient_item in ingredient_items:
            ingredient_item_lines = ingredient_item.text.split('\n')
            quantity, unit = ingredient_item_lines[0].split(' ')
            ingredients_data['ingredients'].append({'quantity': quantity, 'unit': unit, 'name': ingredient_item_lines[1]})
        return ingredients_data

    def _get_nutrients(self, nutrients_element):
        nutrient_lines = nutrients_element.text.replace(' kcal', '').replace(' g', '').split('\n')
        nutrients_values = {
            'calories': nutrient_lines[6],
            'fat': nutrient_lines[8],
            'saturated_fat': nutrient_lines[10],
            'carbs': nutrient_lines[12],
            'sugar': nutrient_lines[14],
            'protein': nutrient_lines[16],
            'salt': nutrient_lines[18],
        }
        return nutrients_values

    def _get_instructions(self, instructions_element):
        instructions_steps = instructions_element.find_elements(By.CSS_SELECTOR, 'div[data-test-id="instruction-step"]')
        instructions_text = [instruction_step.text for instruction_step in instructions_steps]
        instruction_image_links = []
        for instruction_step in instructions_steps:
            try:
                instruction_image_links.append(instruction_step.find_element(By.CSS_SELECTOR, 'img').get_attribute('src'))
            except NoSuchElementException:
                instruction_image_links.append(None)

        instruction_values = {
            'instructions': instructions_text,
            'instruction_images': instruction_image_links
        }
        return instruction_values

    def _get_pdf(self, instructions_element):
        return {'pdf_link': instructions_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')}

    def _get_recipe_category_paths(self) -> list[str]:
        """
        Get all recipe categories from the HelloFresh website.

        Returns:
            List of recipe category paths.
        """
        driver = webdriver.Chrome()
        driver.get(self.base_link)
        category_link_elements = driver.find_elements(By.CSS_SELECTOR, 'a')
        category_links = [category.get_attribute('href') for category in category_link_elements]
        category_paths = self._clean_recipe_category_paths(category_links)
        return category_paths

    def _clean_recipe_category_paths(self, category_links: list[str]) -> list[str]:
        """
        Clean and extract category paths from the list of category links.

        Filters out non-relevant links that contain no recipe IDs (e.g. 65d4898f6c4f22398987607a)
         or are not from the base link.

        Args:
            category_links: List of category links.

        Returns:
            List of cleaned category paths.
        """
        category_links = list(set(category_links))  # only keep unique links
        filtered_links = [link for link in category_links if self.base_link in link]
        filtered_links = [link.split('&')[0] for link in filtered_links]
        filtered_links = [link for link in filtered_links if len(link.split('-')[-1]) != 24]
        category_paths = [link.split('/')[-1] for link in filtered_links]
        return category_paths


if __name__ == "__main__":
    scraper = HelloFreshScraper()
    scraper.get_all_recipes(
        use_stored_links=True,
        save_results=True
    )
