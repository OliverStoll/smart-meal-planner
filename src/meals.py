import pandas as pd
import ast
import os

from utils.logger import create_logger


class HF_Meal_Manager:
    log = create_logger('HF-Messager')
    data_path = 'data/cleaned_data_v2.csv'
    ingredients_df_path = 'data/ingredients_v2.csv'
    pdf_path = 'data/pdfs_v2_mobile'
    orig_portions = 2
    home_ingredients = [
        'milder Chili-Mix', 'Gewürzmischung', 'zwiebel', 'schalotte', 'knoblauch',
        'ketchup', 'mayonnaise', 'sojasoße', 'tomatenmark', 'gemüsebrüh', 'piment', 'senf',
        'wasser', 'Madras Curry', 'Madras-Curry', 'Schwarzkümmel'
    ]
    category_order = ['Obst', 'Gemüse', 'Gewürze', 'Brot', 'Fleisch', 'Haltbares', 'Milchprodukte',
                      'Verschiedenes']

    def __init__(self):
        self.recipe_df = pd.read_csv(self.data_path)
        self.ingredients_df = pd.read_csv(self.ingredients_df_path)

    def get_recipe_ingredients_pdfs(
            self, num_recipes, num_portions=2, meal_type='alle', max_duration=90, min_calories=0
    ):
        recipes = self.get_recipes_filtered_by_user_settings(num_recipes, meal_type, max_duration, min_calories)
        ingredient_shopping_list = self.get_ingredients_shopping_list(recipes, num_portions)
        recipes_pdf_paths = self.get_pdf_paths_from_recipes(recipes, num_portions)
        return ingredient_shopping_list, recipes_pdf_paths

    def get_recipes_filtered_by_user_settings(
            self, num_recipes: int, meal_type: str, max_duration: int, min_calories: int = 0
    ) -> pd.DataFrame:
        recipes_df = self.recipe_df
        recipes_df = self._filter_recipes_by_meal_type(recipes_df, meal_type)
        recipes_df = recipes_df[recipes_df['total_time'] <= max_duration]
        recipes_df = recipes_df[recipes_df['calories'] >= min_calories]
        if num_recipes < len(recipes_df):
            recipes_df = recipes_df.sample(num_recipes)
        recipes_df.reset_index(drop=True, inplace=True)
        return recipes_df

    def _filter_recipes_by_meal_type(self, recipes_df: pd.DataFrame, meal_type: str) -> pd.DataFrame:
        if meal_type == 'vegetarisch':
            tags = ['vegetarisch', 'vegan']
            recipes_df = recipes_df[
                recipes_df['tags'].apply(lambda x: any(tag in x for tag in tags))
            ]
        elif meal_type == 'vegan':
            tags = ['vegan']
            recipes_df = recipes_df[
                recipes_df['tags'].apply(lambda x: any(tag in x for tag in tags))
            ]
        elif meal_type == 'alle':
            negativ_tags = ['vegetarisch', 'vegan']
            recipes_df = recipes_df[
                recipes_df['tags'].apply(lambda x: not any(tag in x for tag in negativ_tags))
            ]
        return recipes_df

    def get_pdf_title_from_meal_name(self, meal_name: str) -> str:
        pdf_title = meal_name.replace(':', '').replace('!', '').replace('&', 'und')
        return pdf_title

    def get_pdf_paths_from_recipes(self, recipes: pd.DataFrame, num_portions: int) -> list[str]:
        titles = recipes['title'].tolist()
        self.log.info(f"Recipes: {titles}")
        pdf_dir = self.pdf_path
        pdf_with_portions_dir = f"{pdf_dir}/{num_portions}"
        if os.path.exists(pdf_with_portions_dir):
            pdf_dir = pdf_with_portions_dir
            self.log.info(f"Using PDFs with portions: {num_portions}")
        _pdf_paths = [f"{pdf_dir}/{self.get_pdf_title_from_meal_name(title)}.pdf" for title in titles]
        for pdf in _pdf_paths:
            if not os.path.exists(pdf):
                self.log.error(f"PDF not found: {pdf}")
        return _pdf_paths

    def get_ingredients_shopping_list(
            self,
            recipes_df: pd.DataFrame,
            num_portions: int,
            filter_home_ingredients: bool = True,
            sorting: str = 'category'
    ) -> str:
        ingredients_df = self._get_ingredient_data(recipes_df, filter_home_ingredients)
        ingredients_df = pd.merge(ingredients_df, self.ingredients_df[['name', 'category']],
                                  on='name', how='left')
        ingredients_df['category'] = pd.Categorical(
            values=ingredients_df['category'],
            categories=self.category_order,
            ordered=True
        )
        if sorting == 'category':
            ingredients_df = ingredients_df.sort_values(['category', 'name'])
        elif sorting == 'amount':
            ingredients_df['is_stueck'] = ingredients_df['unit'] == 'Stück'
            ingredients_df = ingredients_df.sort_values(by=['is_stueck', 'quantity'],
                                                        ascending=False)
            ingredients_df.drop(columns='is_stueck', inplace=True)
        factor = float(num_portions / self.orig_portions)
        ingredients_df['quantity'] = ingredients_df['quantity'] * factor
        ingredients_df['quantity'] = ingredients_df['quantity'].apply(
            lambda x: int(x) if x == int(x) else x)
        max_quantity = ingredients_df['quantity'].max()
        ingredients_df['unit'] = ingredients_df['unit'].replace('Stück', '')
        quantity_digits = len(str(int(max_quantity)))
        ingredients_list_str = ""
        for idx, row in ingredients_df.iterrows():
            if not row['quantity'] == int(row['quantity']):
                quantity_str = f"{row['quantity']:{quantity_digits}.1f}"
            else:
                quantity_str = f"{row['quantity']:{quantity_digits}.0f}"
            ingredients_list_str += f"{quantity_str} {row['unit']:2} {row['name']}\n"
        return ingredients_list_str

    def _get_ingredient_data(self, recipes: pd.DataFrame, filter_home_ingredients) -> pd.DataFrame:
        ingredients = self._collect_ingredients(recipes)
        ingredients_df = pd.DataFrame(ingredients)
        ingredients_df['quantity'] = ingredients_df['quantity'].replace({
            '½': '0.5',
            '¼': '0.25',
            '¾': '0.75',
            '⅓': '0.333',
            '⅔': '0.667',
            '⅕': '0.2',
            '⅛': '0.125',
            '⅜': '0.375',
            '⅝': '0.625',
            '⅞': '0.875'
        })
        final_ingredients = self._sum_up_duplicate_ingredients(ingredients_df)
        if filter_home_ingredients:
            final_ingredients = self._filter_ingredients(final_ingredients)
        return final_ingredients

    def _collect_ingredients(self, recipes: pd.DataFrame) -> list:
        ingredients_series = recipes['ingredients'].tolist()
        all_ingredients = []
        for ingredient_list_str in ingredients_series:
            ingredient_list = ast.literal_eval(ingredient_list_str)
            for ingredient in ingredient_list:
                all_ingredients.append(ingredient)
        return all_ingredients

    def _sum_up_duplicate_ingredients(self, ingredients_df: pd.DataFrame) -> pd.DataFrame:
        ingredients_df['quantity'] = ingredients_df['quantity'].astype(float)
        ingredients_group = ingredients_df.groupby(['name', 'unit'])
        ingredients_df = ingredients_group.agg({'quantity': 'sum'})
        ingredients_df.reset_index(inplace=True)
        return ingredients_df

    def _filter_ingredients(self, ingredients_df: pd.DataFrame) -> pd.DataFrame:
        pattern = '|'.join(self.home_ingredients)
        ingredients_df = ingredients_df[~ingredients_df['name'].str.contains(pattern, case=False)]
        return ingredients_df


if __name__ == '__main__':
    messager = HF_Meal_Manager()
    groceries, pdf_paths = messager.get_recipe_ingredients_pdfs(3, meal_type='vegetarisch')
    print(groceries)
