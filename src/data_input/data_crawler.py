from time import sleep
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
import pandas as pd
from utils.config import create_logger


class HelloFreshScraper:
    log = create_logger('HelloFreshScraper')
    base_link = "https://www.hellofresh.de/recipes/"
    categories = ['schnelle-gerichte']
    temp_csv_path = 'data/temp_csv'
    element_selectors = {
        'description': 'div[data-test-id="recipe-description"]',
        'times': 'div[data-test-id="recipe-description"]',
        'ingredients': 'div[data-test-id="ingredients-list"]',
        'nutrients': 'div[data-test-id="nutritions"]',
        'instructions': 'div[data-test-id="instructions"]',
        'pdf': 'div[data-test-id="instructions"]'
    }  # todo: refactor to combine with getter functions

    def __init__(self):
        self.driver = webdriver.Chrome()
        self.getter_functions = [self._get_description, self._get_times, self._get_ingredients, self._get_nutrients, self._get_instructions, self._get_pdf]
        self.categories = self._get_categories()
        self.log_counter = 0

    def get_all_recipes_details(self, save_to_csv=True):
        category_dfs = []
        for idx, category in enumerate(self.categories):
            self.log.info(f"Category {category}: ({idx+1}/{len(self.categories)})")
            category_df = self.get_all_recipes_details_of_category(category)
            category_dfs.append(category_df)
        recipes_df = pd.concat(category_dfs)
        self.log.info(f"Length raw: {len(recipes_df)}")
        cleaned_df = recipes_df.dropna()
        cleaned_df = cleaned_df.drop_duplicates(subset=['pdf_link'])
        self.log.info(f"Length cleaned: {len(cleaned_df)}")
        if save_to_csv:
            recipes_df.to_csv(f'{self.temp_csv_path}/recipes.csv', index=False)
            cleaned_df.to_csv(f'{self.temp_csv_path}/cleaned.csv', index=False)
            self.log.info("Recipes saved to csv")
        return recipes_df

    def get_all_recipes_details_of_category(self, category):
        links = self.get_recipes_links_of_category(category=category)
        self.log_counter = 0
        recipes_category_df = pd.DataFrame()
        for link in links:
            try:
                recipe_values = self.get_single_recipe_details(link)
                recipes_category_df = recipes_category_df._append(recipe_values, ignore_index=True)
            except Exception as e:
                self.log.error(f"Error in getting details from {link}: {e}")
        recipes_category_df['category'] = category
        return recipes_category_df

    def get_recipes_links_of_category(self, category):
        link = f"{self.base_link}/{category}?page=999"
        self.driver.get(link)
        sleep(3)
        # scroll down to load all recipes
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        recipe_links = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-test-id="recipe-image-card"] > a')
        recipe_links_href = [recipe_link.get_attribute('href') for recipe_link in recipe_links]
        recipe_links_href = [link for link in recipe_links_href if len(link.split('-')[-1]) == 24]
        recipe_links_href = list(set(recipe_links_href))  # only keep unique links
        self.log.info(f"Found {len(recipe_links_href)} recipes in category {category}")
        return recipe_links_href

    def get_single_recipe_details(self, link):
        self.driver.get(link)
        recipe_values = {'recipe-link': link}
        for idx, getter_function in enumerate(self.getter_functions):
            element = self.driver.find_element(By.CSS_SELECTOR, self.element_selectors[list(self.element_selectors.keys())[idx]])
            try:
                values = getter_function(element)  # noqa
            except NoSuchElementException:
                self.log.warn(f"{getter_function.__name__.replace('_get_', '').upper()} not found: {link}")
                continue
            except Exception as e:
                self.log.warn(f"Error in {getter_function.__name__}: {link} - {e}")
                continue
            recipe_values.update(values)
        self.log_counter += 1
        self.log.debug(f"[{self.log_counter}] {recipe_values['title']}")
        return recipe_values

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

    def _get_categories(self):
        base_link = "https://www.hellofresh.de/recipes/"
        driver = webdriver.Chrome()
        driver.get(base_link)
        categories = driver.find_elements(By.CSS_SELECTOR, 'a')
        category_links = [category.get_attribute('href') for category in categories]
        category_links = [link for link in category_links if base_link in link]
        category_links = [link.split('&')[0] for link in category_links]
        # filter links that contain an id like this: 65d4898f6c4f22398987607a (recipes)
        filtered_links = [link for link in category_links if len(link.split('-')[-1]) != 24]
        categories = [link.split('/')[-1] for link in filtered_links]
        return categories



if __name__ == "__main__":
    scraper = HelloFreshScraper()
    scraper.get_all_recipes_details(save_to_csv=True)
    # scraper.get_recipes_links_of_category('schnelle-gerichte')
    # scraper.get_single_recipe_details('https://www.hellofresh.de/recipes/vegetarische-gnocchi-mit-brokkoli-und-asiatischem-pesto-64c2f0e7b1a6f4f0d9a8c3d3')
