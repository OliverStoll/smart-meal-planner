import pandas as pd
import ast
import os
from typing import Literal
from common_utils.logger import create_logger
from common_utils.config import ROOT_DIR

from src.telegram.callbacks.settings_types import UserSettings


class RecipeManager:
    """ Handles recipe data, generating shopping lists and PDF paths for recipes."""

    log = create_logger('Recipe Messager')
    orig_portions = 2
    home_ingredients = [
        'milder Chili-Mix', 'Gewürzmischung', 'zwiebel', 'schalotte', 'knoblauch',
        'ketchup', 'mayonnaise', 'sojasoße', 'tomatenmark', 'gemüsebrüh', 'piment', 'senf',
        'wasser', 'Madras Curry', 'Madras-Curry', 'Schwarzkümmel'
    ]
    category_order = ['Obst', 'Gemüse', 'Gewürze', 'Brot', 'Fleisch', 'Haltbares', 'Milchprodukte', 'Verschiedenes']
    quantity_replace_map = {
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
    }
    unit_replace_map = {
        'Stück': '',
        'Packung': 'Pk',
    }

    def __init__(
            self,
            data_path='data/temp_data/cleaned.csv',                         # 'data/recipes/cleaned_data_v2.csv',
            ingredients_df_path='data/temp_data/ingredients_manual.csv',    # recipes/ingredients_v2.csv',
            pdf_paths='data/temp_pdfs'
    ):
        self.recipes = pd.read_csv(data_path)
        self.ingredients_df = pd.read_csv(ingredients_df_path)
        self.pdf_path = pdf_paths

    def sample_fitting_recipes(
            self,
            num_recipes: int,
            user_settings: UserSettings,
            recipes: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Filters the recipes based on user settings and returns a DataFrame of selected recipes.

        Args:
            num_recipes: The number of recipes to return.
            user_settings: The user settings containing meal type, max duration, and min calories.
            recipes: Optional; if provided, it will be used instead of the default recipes DataFrame.

        Returns:
            A DataFrame containing the filtered recipes.
        """
        if recipes is None:
            recipes = self.get_recipes_filtered_by_user_settings(user_settings=user_settings)

        if num_recipes < len(recipes):
            recipes = recipes.sample(num_recipes)

        recipes.reset_index(drop=True, inplace=True)

        return recipes

    def get_num_of_recipes_filtered_by_user_settings(
            self,
            user_settings: UserSettings,
            recipes: pd.DataFrame | None = None) -> int:
        """
        Filter the recipes based on user settings and returns the number of selected recipes.
        """
        recipes_df = self.get_recipes_filtered_by_user_settings(user_settings=user_settings, recipes=recipes)
        return len(recipes_df)

    def get_recipes_filtered_by_user_settings(
            self,
            user_settings: UserSettings,
            recipes: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """
        Filters the recipes based on user settings and returns the number of selected recipes.

        Args:
            user_settings: The user settings containing meal type, max duration, and min calories.
            recipes: Optional; if provided, will be used instead of the default DataFrame of all recipes.

        Returns:
            An integer representing the number of filtered recipes.
        """
        recipes_df = recipes or self.recipes
        recipes_df = self._filter_recipes_by_meal_type(recipes_df=recipes_df, meal_type=user_settings.meal_type)
        recipes_df = recipes_df[recipes_df['total_time'] <= user_settings.max_duration]
        recipes_df = recipes_df[recipes_df['calories'] >= user_settings.cal_min]

        return recipes_df

    @staticmethod
    def _filter_recipes_by_meal_type(recipes_df: pd.DataFrame, meal_type: str) -> pd.DataFrame:
        if meal_type == 'vegetarisch':
            tags = ['vegetarisch', 'vegan']
            recipes_df = recipes_df[recipes_df['tags'].apply(lambda x: any(tag in x.lower() for tag in tags))]
        elif meal_type == 'vegan':
            tags = ['vegan']
            recipes_df = recipes_df[recipes_df['tags'].apply(lambda x: any(tag in x.lower() for tag in tags))]
        elif meal_type == 'protein':
            negativ_tags = ['vegetarisch', 'vegan']
            recipes_df = recipes_df[recipes_df['tags'].apply(lambda x: not any(tag in x for tag in negativ_tags))]
        return recipes_df

    @staticmethod
    def get_pdf_title_from_meal_name(meal_name: str) -> str:
        pdf_title = meal_name.replace(':', '').replace('!', '').replace('&', 'und')
        return pdf_title

    def get_ingredients_shopping_list(
            self,
            recipes_df: pd.DataFrame,
            num_portions: int,
            filter_home_ingredients: bool = True,
            sorting: Literal['category', 'amount'] = 'category'
    ) -> str:
        """
        Generates a combined shopping list from the recipes DataFrame, taking into account the number of portions.

        Args:
            recipes_df (pd.DataFrame): DataFrame containing the recipes.
            num_portions (int): Number of portions to adjust the quantities.
            filter_home_ingredients (bool): Whether to filter out home ingredients.
            sorting (str): Sorting method for the ingredients list ('category' or 'amount').
        """
        ingredients_df = self._get_ingredient_data(recipes_df, filter_home_ingredients)
        ingredients_df = self._sort_ingredients_data(ingredients_df, sorting)

        ingredients_df['unit'] = ingredients_df['unit'].replace(self.unit_replace_map)
        quantity_factor = float(num_portions / self.orig_portions)
        ingredients_df['quantity'] = ingredients_df['quantity'] * quantity_factor
        # round all quantities if unit is not 'Stück'
        ingredients_df['quantity'] = ingredients_df.apply(
            lambda x: round(x['quantity']) if x['quantity'] > 2 else x['quantity'], axis=1
        )
        ingredients_df['quantity'] = ingredients_df.apply(
            lambda x: round(x['quantity'], -1) if x['quantity'] > 20 else x['quantity'], axis=1
        )
        ingredients_df['quantity'] = ingredients_df.apply(
            lambda x: round(x['quantity'], -2) if x['quantity'] > 300 else x['quantity'], axis=1
        )
        ingredients_df['quantity'] = ingredients_df['quantity'].apply(lambda x: int(x) if x == int(x) else x)
        ingredients_df['unit'] = ingredients_df['unit'].replace('Stück', '')
        ingredients_list_str = self._generate_ingredients_shopping_list_text(ingredients_df)
        return ingredients_list_str

    def get_recipes_by_id(self, recipe_ids: list[str]) -> pd.DataFrame:
        """
        Retrieves recipes based on the provided recipe IDs.

        Args:
            recipe_ids (list[str]): List of recipe IDs.

        Returns:
            pd.DataFrame: DataFrame containing the recipes corresponding to the provided IDs.
        """
        recipes_df = self.recipes[self.recipes['id'].isin(recipe_ids)]
        return recipes_df

    def get_recipe_titles_by_id(self, recipe_ids: list[str]) -> list[str]:
        """
        Retrieves recipe names based on the provided recipe IDs.

        Args:
            recipe_ids (list[str]): List of recipe IDs.

        Returns:
            list[str]: List of recipe names corresponding to the provided IDs.
        """
        recipes_df = self.recipes[self.recipes['id'].isin(recipe_ids)]
        return recipes_df['title'].tolist()

    def _sort_ingredients_data(
            self,
            ingredients_df: pd.DataFrame,
            sorting: Literal['category', 'amount']
    ) -> pd.DataFrame:
        """
        Sorts the ingredients DataFrame based on the specified sorting method, either by their categories or amounts.

        Args:
            ingredients_df (pd.DataFrame): DataFrame containing the ingredients.
            sorting (str): Sorting method for the ingredients list ('category' or 'amount').

        Returns:
            Sorted DataFrame of ingredients.
        """
        ingredients_df['is_stueck'] = ingredients_df['unit'] == 'Stück'
        if sorting == 'category':
            ingredients_df = ingredients_df.sort_values(['category', 'is_stueck', 'quantity'], ascending=[True, False, False])
        elif sorting == 'amount':
            ingredients_df = ingredients_df.sort_values(by=['is_stueck', 'quantity'], ascending=False)
        ingredients_df.drop(columns='is_stueck', inplace=True)

        return ingredients_df

    @staticmethod
    def _generate_ingredients_shopping_list_text(ingredients_df: pd.DataFrame, min_digits: int = 3) -> str:
        max_quantity = ingredients_df['quantity'].max()
        quantity_digits = len(str(int(max_quantity)))
        quantity_digits = min(quantity_digits, min_digits)
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
        ingredients_df['quantity'] = ingredients_df['quantity'].replace(self.quantity_replace_map)

        unique_ingredients = self._sum_up_duplicate_ingredients(ingredients_df)

        if filter_home_ingredients:
            unique_ingredients = self._filter_ingredients(unique_ingredients, self.home_ingredients)

        unique_ingredients = self._clean_ingredient_data(unique_ingredients)

        return unique_ingredients

    def _clean_ingredient_data(self, ingredients_df: pd.DataFrame) -> pd.DataFrame:
        ingredients_df['quantity'] = ingredients_df['quantity'].replace(self.quantity_replace_map)

        ingredients_df = pd.merge(
            left=ingredients_df,
            right=self.ingredients_df[['name', 'category']],
            on='name',
            how='left'
        )
        ingredients_df['category'] = pd.Categorical(
            values=ingredients_df['category'],
            categories=self.category_order,
            ordered=True
        )
        return ingredients_df

    @staticmethod
    def _collect_ingredients(recipes: pd.DataFrame) -> list:
        ingredients_series = recipes['ingredients'].tolist()
        all_ingredients = []
        for ingredient_list_str in ingredients_series:
            ingredient_list = ast.literal_eval(ingredient_list_str)
            for ingredient in ingredient_list:
                all_ingredients.append(ingredient)
        return all_ingredients

    @staticmethod
    def _sum_up_duplicate_ingredients(ingredients_df: pd.DataFrame) -> pd.DataFrame:
        ingredients_df['quantity'] = ingredients_df['quantity'].astype(float)
        ingredients_group = ingredients_df.groupby(['name', 'unit'])
        ingredients_df = ingredients_group.agg({'quantity': 'sum'})
        ingredients_df.reset_index(inplace=True)
        return ingredients_df

    @staticmethod
    def _filter_ingredients(ingredients_df: pd.DataFrame, ingredients_to_filter: list[str]) -> pd.DataFrame:
        pattern = '|'.join(ingredients_to_filter)
        ingredients_df = ingredients_df[~ingredients_df['name'].str.contains(pattern, case=False)]
        return ingredients_df
