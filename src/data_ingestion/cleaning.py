import ast
import pandas as pd
import re
import logging
from sqlalchemy.types import JSON

from data_ingestion import (
    REPLACE_INGREDIENTS_STRINGS,
    REPLACE_TITLE_STRINGS,
    REPLACE_INSTRUCTIONS_STRINGS,
    REPLACE_INSTRUCTION_PATTERNS,
    KJ_TO_KCAL,
)
from database import RAW_RECIPES_REF, CLEANED_RECIPES_REF
from database.engine import df_from_sql, df_to_sql

log = logging.getLogger(__name__)


def clean_recipes_data(recipes: pd.DataFrame) -> pd.DataFrame:
    """apply all cleaning functions to the dataframe. Already expects unique recipes"""
    recipes = remove_duplicate_recipes(recipes)
    recipes = remove_recipes_with_missing_data(recipes)
    recipes = clean_category_column(recipes)
    recipes = clean_instructions_column(recipes)
    recipes = clean_ingredients_column(recipes)
    recipes = clean_calories_column(recipes)
    recipes = clean_title_column(recipes)
    # recipes['total_time'] = format_cooking_time(recipes['total_time'])
    recipes.rename(columns={"cooking_time": "difficulty"}, inplace=True)
    return recipes


def remove_duplicate_recipes(recipes: pd.DataFrame) -> pd.DataFrame:
    for column in ["id", "link", "title"]:
        recipes = recipes.drop_duplicates(subset=[column], keep="first")
    return recipes


def remove_recipes_with_missing_data(recipes: pd.DataFrame) -> pd.DataFrame:
    for column in ["ingredients", "instructions", "title"]:
        recipes = recipes[recipes[column].notnull()]
    return recipes


def clean_category_column(recipes: pd.DataFrame) -> pd.DataFrame:
    recipes["category_friendly"] = recipes["category"]
    for replace_str in [
        "e-rezepte",
        "e-gerichte",
        "s-rezepte",
        "rezepte-",
        "-rezepte",
    ]:
        recipes["category_friendly"] = recipes["category_friendly"].str.replace(replace_str, "")
    return recipes


def clean_instructions_column(df: pd.DataFrame) -> pd.DataFrame:
    df["instructions"] = df.apply(lambda row: _get_recipe_instructions(row), axis=1)
    return df


def _get_recipe_instructions(recipe_entry: pd.Series, first_steps_to_ignore: int = 2) -> list[list[str]]:
    """
    Get the raw instruction text from the recipe entry and split it into a list of steps.
    Each step is formatted as a list of strings, where each string is a line of instruction.

    Args:
         recipe_entry: A single recipe entry from the dataframe.
        first_steps_to_ignore: Number of initial steps to ignore in the instruction.

    Returns:
        A list of lists, where each inner list contains the lines of a single instruction step.
    """
    instruction_steps = ast.literal_eval(recipe_entry["instructions"])
    for replace_pattern, replace_value in REPLACE_INSTRUCTION_PATTERNS.items():
        instruction_steps = [re.sub(replace_pattern, replace_value, x) for x in instruction_steps]
    for replace_str, replace_value in REPLACE_INSTRUCTIONS_STRINGS.items():
        instruction_steps = [x.replace(replace_str, replace_value) for x in instruction_steps]
    instruction_steps = [x[first_steps_to_ignore:].split("\n") for x in instruction_steps]
    all_instruction_lines = []
    for instruction_step in instruction_steps:
        instruction_step_lines = []
        for line in instruction_step:
            instruction_step_lines += _process_single_instruction_line(line)
        all_instruction_lines.append(instruction_step_lines)
    return all_instruction_lines


def clean_title_column(recipes: pd.DataFrame) -> pd.DataFrame:
    """Clean the title column by removing special characters and replacing certain strings"""
    for replace_str, replace_value in REPLACE_TITLE_STRINGS.items():
        recipes["title"] = recipes["title"].str.replace(replace_str, replace_value)
    recipes["title"] = recipes["title"].str.strip()
    return recipes


def _clean_recipe_ingredients(recipe_entry: pd.Series) -> list[dict]:
    """
    Clean the ingredients column by replacing certain strings and splitting paired ingredients.

    Args:
        recipe_entry: A single recipe entry from the dataframe.

    Returns:
        A list of cleaned ingredient entries with 'name', 'quantity', and 'unit' keys.
    """
    if not recipe_entry["ingredients"]:
        log.warning(f"No ingredients found for recipe: {recipe_entry['title']}")
        return []
    for key, value in REPLACE_INGREDIENTS_STRINGS.items():
        recipe_entry["ingredients"] = recipe_entry["ingredients"].replace(key, value)
        recipe_entry["ingredients"] = recipe_entry["ingredients"].strip()
    try:
        ingredient_entries = ast.literal_eval(recipe_entry["ingredients"])
        cleaned_ingredients = _split_all_paired_ingredients(ingredient_entries)
    except Exception as e:
        print(f"Error in cleaning ingredients for {recipe_entry['title']}: {e}")
        return []

    return cleaned_ingredients


def _split_all_paired_ingredients(ingredients_entries: list[dict]) -> list[dict]:
    """
    Split all ingredients that are paired with a '/' into two separate entries.

    Args:
        ingredients_entries: A list of ingredient entries, each entry is a dictionary with
         'name', 'quantity', and 'unit'.

    Returns:
        A list of ingredient entries with 'name', 'quantity', and 'unit' keys, where all ingredients are split.
    """
    cleaned_ingredients = []
    for ingredient_entry in ingredients_entries:
        if "/" in ingredient_entry["name"]:
            first_ingredient, second_ingredient = _split_ingredient_entry(ingredient_entry)
            cleaned_ingredients.append(first_ingredient)
            cleaned_ingredients.append(second_ingredient)
        else:
            cleaned_ingredients.append(ingredient_entry)
    return cleaned_ingredients


def clean_ingredients_column(recipes: pd.DataFrame) -> pd.DataFrame:
    recipes["ingredients"] = recipes.apply(lambda x: _clean_recipe_ingredients(x), axis=1)
    return recipes


def _split_ingredient_entry(ingredient: dict) -> tuple[dict, dict]:
    split_quantity = int(int(ingredient["quantity"]) / 2)
    split_ingredient = {
        "name": ingredient["name"].split("/")[1],
        "quantity": split_quantity,
        "unit": ingredient["unit"],
    }
    ingredient["name"] = ingredient["name"].split("/")[0]
    ingredient["quantity"] = split_quantity
    return ingredient, split_ingredient


def clean_calories_column(recipes: pd.DataFrame) -> pd.DataFrame:
    def convert_calories(calories_str: str) -> int | None:
        try:
            if "kJ" in calories_str:
                return int(int(calories_str[:-3]) * KJ_TO_KCAL)
            else:
                return int(calories_str)
        except Exception:
            return None

    recipes["calories"] = recipes["calories"].apply(lambda x: convert_calories(x) if isinstance(x, str) else x)
    return recipes


def _process_single_instruction_line(line):
    def replacer(match):
        number = match.group(1)
        unit = match.group(2).strip()  # Handle case when there's no unit
        return f"[{number} {unit}]" if unit else f"[{number}]"

    line = line.strip()
    if line.endswith("."):
        line = line[:-1]
    if "." in line:
        split_lines = [x.strip() + "." for x in line.split(".")]
    else:
        split_lines = [line.strip() + "."]
    split_lines = [x for x in split_lines if len(x) > 3]
    pattern = r"(\d+(?:,\d+)?)\s*(\w*)\s*\[.*?\]"
    split_lines = [re.sub(pattern, replacer, text) for text in split_lines]
    return split_lines


def _format_cooking_time(
    recipe_time_column: pd.Series,
) -> pd.Series:
    """clean 'x Stunde(n)' in the time columns, by removing it and adding x * 60 minutes"""

    def convert_time_to_minutes(time_str: str) -> float:
        if "eine Stunde" in time_str:
            time_str = time_str.replace("eine Stunde", "").strip()
            remaining_time = float(time_str) if time_str else 0
            return remaining_time + 60
        else:
            return float(time_str)

    recipe_time_column = recipe_time_column.apply(lambda x: convert_time_to_minutes(x) if isinstance(x, str) else x)
    return recipe_time_column


def save_ingredients(recipes: pd.DataFrame) -> None:
    unique_ingredients_count = {}
    ingredients_entries = []
    for idx, row in recipes.iterrows():
        for ingredient in row["ingredients"]:
            name = ingredient["name"]
            unique_ingredients_count[name] = unique_ingredients_count.get(name, 0) + 1
    unique_ingredients_count = {
        k: v for k, v in sorted(unique_ingredients_count.items(), key=lambda item: item[1], reverse=True)
    }
    for name, count in unique_ingredients_count.items():
        log.debug(f"{count}: {name}")
        ingredients_entries.append({"name": name, "count": count})
    ingredients = pd.DataFrame(ingredients_entries)
    df_to_sql(ref="ingredients", df=ingredients)


if __name__ == "__main__":
    raw_recipes = df_from_sql(RAW_RECIPES_REF)
    cleaned_recipes = clean_recipes_data(raw_recipes)
    df_to_sql(
        ref=CLEANED_RECIPES_REF,
        df=cleaned_recipes,
        dtype={"ingredients": JSON, "instructions": JSON, "instruction_images": JSON},
    )
    save_ingredients(cleaned_recipes)
