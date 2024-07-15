import pandas as pd
import ast
import os

from utils.logger import create_logger


class HF_Meal_Manager:
    log = create_logger('HF-Messager')
    file_path = '../data/unique_recipes.csv'
    ingredients_df_path = '../data/ingredients.csv'
    pdf_path = '../pdfs'
    home_ingredients = ['zwiebel', 'schalotte', 'knoblauch', 'ketchup', 'tomatenmark', 'hartkäse', 'gemüsebrüh', 'reis', 'piment', 'senf', 'wasser']
    category_order = ['Obst', 'Gemüse', 'Gewürze', 'Brot', 'Fleisch', 'Milchprodukte', 'Verschiedenes']

    def __init__(self):
        self.recipe_df = pd.read_csv(self.file_path)
        self.ingredients_df = pd.read_csv(self.ingredients_df_path)

    def get_recipes(self, num_recipes):
        recipes = self.recipe_df.sample(num_recipes)
        ingredient_summary = self.get_ingredients_summary(recipes)
        pdf_paths = self.get_recipe_pdfs(recipes)
        return ingredient_summary, pdf_paths

    def get_recipe_pdfs(self, recipes):
        titles = recipes['title'].tolist()
        self.log.info(f"Recipes: {titles}")
        pdf_paths = [f"{self.pdf_path}/{title.replace(' ', '_').replace(':', ',')}.pdf" for title in titles]
        for pdf in pdf_paths:
            if not os.path.exists(pdf):
                self.log.error(f"PDF not found: {pdf}")
            else:
                self.log.debug(f"Sending PDF: {pdf}")
        return pdf_paths

    def get_ingredients_summary(self, recipes):
        ingredients_df = self._get_ingredient_data(recipes)
        ingredients_df = pd.merge(ingredients_df, self.ingredients_df[['name', 'category']], on='name', how='left')
        ingredients_df['category'] = pd.Categorical(ingredients_df['category'],
                                                    categories=self.category_order,
                                                    ordered=True)
        ingredients_df = ingredients_df.sort_values('category')
        ingredients_str = ""
        for idx, row in ingredients_df.iterrows():
            unit = row['unit'].replace('Stück', '')
            ingredients_str += f"{row['quantity']:3.0f} {unit:2} {row['name']}\n"
        ingredients_str = self._fix_ingredient_str_for_telegram(ingredients_str)
        return ingredients_str

    def _fix_ingredient_str_for_telegram(self, ingredient_str):
        ingredient_str = ingredient_str.replace('    ', '      ')
        ingredient_str = ingredient_str.replace(' g  ', ' g   ')
        lines = ingredient_str.split('\n')
        doubled_lines = []

        for line in lines:
            if line.startswith('  '):
                doubled_line = '    ' + line[2:]
            elif line.startswith(' '):
                doubled_line = '  ' + line[1:]
            else:
                doubled_line = line
            doubled_lines.append(doubled_line)

        return '\n'.join(doubled_lines)


    def _get_ingredient_data(self, recipes):
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
    messager = HF_Meal_Manager()
    groceries, pdf_paths = messager.get_recipes(3)
    print(groceries)



