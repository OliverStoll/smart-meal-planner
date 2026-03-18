from typing import Literal

import pandas as pd

from messaging import QUANTITY_REPLACE_MAP, home_ingredients, UNIT_REPLACE_MAP

ORIGINAL_PORTIONS = 2


def ingredients_shopping_list(
    recipes: pd.DataFrame,
    num_portions: int,
    filter_home_ingredients: bool = True,
    sorting: Literal["category", "amount"] = "amount",  # TODO
) -> str:
    """
    Generates a combined shopping list from the recipes DataFrame, taking into account the number of portions.

    Args:
        recipes (pd.DataFrame): DataFrame containing the recipes.
        num_portions (int): Number of portions to adjust the quantities.
        filter_home_ingredients (bool): Whether to filter out home ingredients.
        sorting (str): Sorting method for the ingredients list ('category' or 'amount').
    """
    ingredients = ingredients_from_recipes(recipes)
    ingredients = clean_ingredient_data(ingredients, filter_home_ingredients)
    ingredients = sort_ingredients_data(ingredients, sorting)
    ingredients = clean_ingredients_quantity_data(ingredients, num_portions)
    ingredients_list_str = _generate_ingredients_shopping_list_text(ingredients)
    return ingredients_list_str


def ingredients_from_recipes(recipes: pd.DataFrame) -> pd.DataFrame:
    ingredients_series = recipes["ingredients"].tolist()
    all_ingredients = []
    for ingredient_list in ingredients_series:
        for ingredient in ingredient_list:
            all_ingredients.append(ingredient)
    return pd.DataFrame(all_ingredients)


def clean_ingredient_data(ingredients: pd.DataFrame, filter_home_ingredients: bool) -> pd.DataFrame:
    ingredients["quantity"] = ingredients["quantity"].replace(QUANTITY_REPLACE_MAP)
    ingredients = _sum_up_duplicate_ingredients(ingredients)
    if filter_home_ingredients:
        pattern = "|".join(home_ingredients)
        ingredients = ingredients[~ingredients["name"].str.contains(pattern, case=False)]
    # ingredients = pd.merge(
    #     left=ingredients, right=self.ingredients[["name", "category"]], on="name", how="left"
    # )
    # ingredients["category"] = pd.Categorical(
    #     values=ingredients_df["category"], categories=self.category_order, ordered=True
    # ) # TODO
    return ingredients


def sort_ingredients_data(ingredients: pd.DataFrame, sorting: Literal["category", "amount"]) -> pd.DataFrame:
    """Sorts the ingredients DataFrame based on the sorting method, either by their categories or amounts."""
    ingredients["is_stueck"] = ingredients["unit"] == "Stück"
    if sorting == "category":
        ingredients = ingredients.sort_values(["category", "is_stueck", "quantity"], ascending=[True, False, False])
    elif sorting == "amount":
        ingredients = ingredients.sort_values(by=["is_stueck", "quantity"], ascending=False)
    ingredients.drop(columns="is_stueck", inplace=True)
    return ingredients


def clean_ingredients_quantity_data(ingredients: pd.DataFrame, num_portions: int) -> pd.DataFrame:
    ingredients["unit"] = ingredients["unit"].replace(UNIT_REPLACE_MAP)
    quantity_factor = float(num_portions / ORIGINAL_PORTIONS)
    ingredients["quantity"] = ingredients["quantity"] * quantity_factor
    for min_value, round_digit in [(2, 0), (20, -1), (300, -2)]:  # TODO -> settings
        ingredients["quantity"] = ingredients.apply(
            lambda x: round(x["quantity"], round_digit) if x["quantity"] > min_value else x["quantity"],
            axis=1,
        )
    ingredients["quantity"] = ingredients["quantity"].apply(lambda x: int(x) if x == int(x) else x)
    return ingredients


def _generate_ingredients_shopping_list_text(ingredients: pd.DataFrame, min_digits: int = 3) -> str:
    max_quantity = ingredients["quantity"].max()
    quantity_digits = len(str(int(max_quantity)))
    quantity_digits = min(quantity_digits, min_digits)
    ingredients_list_str = ""
    for idx, row in ingredients.iterrows():
        if not row["quantity"] == int(row["quantity"]):
            quantity_str = f"{row['quantity']:{quantity_digits}.1f}"
        else:
            quantity_str = f"{row['quantity']:{quantity_digits}.0f}"
        ingredients_list_str += f"{quantity_str} {row['unit']:2} {row['name']}\n"
    return ingredients_list_str


def _sum_up_duplicate_ingredients(ingredients_df: pd.DataFrame) -> pd.DataFrame:
    ingredients_df["quantity"] = ingredients_df["quantity"].astype(float)
    ingredients_group = ingredients_df.groupby(["name", "unit"])
    ingredients_df = ingredients_group.agg({"quantity": "sum"})
    ingredients_df.reset_index(inplace=True)
    return ingredients_df
