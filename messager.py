import pandas as pd
import ast

from utils.logger import create_logger


class HelloFreshMessager:
    log = create_logger('HF-Messager')
    file_path = 'hellofresh_recipes.csv'
    home_ingredients = ['zwiebel', 'schalotte', 'knoblauch', 'ketchup', 'tomatenmark', 'hartkäse', 'gemüsebrüh', 'reis', 'piment', 'senf']

    def __init__(self):
        self.recipe_df = pd.read_csv(self.file_path)
        # prepare data
        self.recipe_df = self.recipe_df[~self.recipe_df['ingredients'].isna()]
        self.recipe_df['ingredients'] = self.recipe_df['ingredients'].str.replace('½', '0.5').str.replace('¼', '0.25').str.replace('¾', '0.75')

    def get_ingredients_summary(self, num_recipes=3):
        ingredients_df = self.get_ingredients_data(num_recipes)
        ingredients_str = ""
        for idx, row in ingredients_df.iterrows():
            unit = row['unit'].replace('Stück', '')
            ingredients_str += f"{row['quantity']:4.0f} {unit:2} {row['name']}\n"
        print(ingredients_str)

    def get_ingredients_data(self, num_recipes):
        self.log.info(f"Collecting data for {num_recipes} recipes")
        recipes = self.recipe_df.head(num_recipes)
        ingredients = self._collect_ingredients(recipes)
        ingredients_df = pd.DataFrame(ingredients)
        unique_ingredients = self._merge_ingredients(ingredients_df)
        filtered_ingredients = self._filter_ingredients(unique_ingredients)
        return filtered_ingredients

    def _collect_ingredients(self, recipes):
        ingredients_series = recipes['ingredients'].tolist()
        all_ingredients = []
        for ingredient_list_str in ingredients_series:
            ingredient_list = ast.literal_eval(ingredient_list_str)
            self.log.debug(f"Ingredients: {len(ingredient_list)}")
            for ingredient in ingredient_list:
                all_ingredients.append(ingredient)
        return all_ingredients

    def _merge_ingredients(self, ingredients_df):
        """Merge all ingredient rows that have the same name, by summing up the amount. Throw and error if the unit is different"""
        ingredients_df['quantity'] = ingredients_df['quantity'].astype(float)
        ingredients_df = ingredients_df.groupby('name').agg({'quantity': 'sum', 'unit': 'first'}).reset_index()
        return ingredients_df

    def _filter_ingredients(self, ingredients_df):
        pattern = '|'.join(self.home_ingredients)
        ingredients_df = ingredients_df[~ingredients_df['name'].str.contains(pattern, case=False)]
        ingredients_df = ingredients_df[~ingredients_df['name'].str.contains('Gewürzmischung')]
        return ingredients_df


if __name__ == '__main__':
    messager = HelloFreshMessager()
    df = messager.get_ingredients_summary(3)


