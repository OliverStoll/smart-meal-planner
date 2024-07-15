from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import requests

from utils.config import create_logger


class HelloFreshScraper:
    log = create_logger('HelloFreshScraper')
    base_link = "https://www.hellofresh.de/recipes/"
    categories = ['schnelle-gerichte']
    element_selectors = {
        'description': 'div[data-test-id="recipe-description"]',
        'times': 'div[data-test-id="recipe-description"]',
        'ingredients': 'div[data-test-id="ingredients-list"]',
        'nutrients': 'div[data-test-id="nutritions"]',
        'instructions': 'div[data-test-id="instructions"]'
    }

    def __init__(self):
        self.driver = webdriver.Chrome()
        self.getter_functions = [self._get_description, self._get_times, self._get_ingredients, self._get_nutrients, self._get_instructions]

    def get_all_recipes_details(self, save_to_csv=True):
        links = self.get_recipes_links_of_category()
        recipes_df = pd.DataFrame()
        for link in links:
            recipe_values = self.get_single_recipe_details(link)
            recipes_df = recipes_df._append(recipe_values, ignore_index=True)
        if save_to_csv:
            recipes_df.to_csv('hellofresh_recipes.csv', index=False)
            self.log.info("Recipes saved to csv")
        return recipes_df

    def get_recipes_links_of_category(self):
        link = f"{self.base_link}/{self.categories[0]}?page=999"
        self.driver.get(link)
        # scroll down to load all recipes
        sleep(3)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        recipe_links = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-test-id="recipe-image-card"] > a')
        recipe_links_href = [recipe_link.get_attribute('href') for recipe_link in recipe_links]
        recipe_links_href = recipe_links_href[:-5]
        self.log.debug(len(recipe_links))
        return recipe_links_href


    def get_single_recipe_details(self, link):
        self.driver.get(link)

        recipe_values = {}
        for idx, getter_function in enumerate(self.getter_functions):
            element = self.driver.find_element(By.CSS_SELECTOR, self.element_selectors[list(self.element_selectors.keys())[idx]])
            try:
                values = getter_function(element)
            except Exception as e:
                self.log.error(f"Error in getting values from {getter_function.__name__} for link {link} - {e}")
                continue
            recipe_values.update(values)

        self.log.debug(recipe_values['title'])
        return recipe_values

    def _get_description(self, description_element):
        title = description_element.find_element(By.CSS_SELECTOR, 'h1').text
        description_selector = 'div:nth-child(2) > div:nth-child(2) > div:nth-child(1)'
        description_div = description_element.find_element(By.CSS_SELECTOR, description_selector)
        # TODO: filter tags from description
        description_tags = description_div.text.split('\n')[1].replace('Tags:', '').split('•')
        description_values = {'title': title, 'description': description_div.text, 'tags': description_tags}
        return description_values

    def _get_times(self, description_element):
        selector = 'div:nth-child(2) > div:nth-child(2) > div:nth-child(2)'
        times_div = description_element.find_element(By.CSS_SELECTOR, selector)
        times_lines = times_div.text.replace(' Minuten', '').split('\n')
        times_values = {'total_time': times_lines[1], 'preparation_time': times_lines[3], 'dificulty': times_lines[5]}
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
        instruction_values = {
            'instructions': instructions_text,
            'pdf_link': instructions_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
        }
        return instruction_values



if __name__ == "__main__":
    # scraper = HelloFreshScraper()
    # links = scraper.get_recipes_links_of_category()
    # scraper.get_single_recipe_details(SINGLE_LINK)
    # scraper.get_all_recipes_details()
    # sleep(1000)

    download_all_pdfs()
