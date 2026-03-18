from unittest.mock import Mock, ANY

import pandas as pd
import pandas.testing as pdt

from data_ingestion.cleaning import (
    clean_recipes_data,
    _format_cooking_time,
    save_ingredients,
)


class TestDataCleaning:
    def test_clean_recipes_data(self, raw_recipes):
        cleaned_recipes = clean_recipes_data(raw_recipes)
        assert "ingredients" in cleaned_recipes.columns, "Expected 'ingredients' column after cleaning"
        assert "instructions" in cleaned_recipes.columns, "Expected 'instructions' column after cleaning"
        assert (
            cleaned_recipes["ingredients"].apply(lambda x: isinstance(x, list)).any()
        ), "Expected 'ingredients' to be a list"
        assert (
            cleaned_recipes["instructions"].apply(lambda x: isinstance(x, list)).any()
        ), "Expected 'instructions' to be a list"


def test_format_cooking_time():
    series = pd.Series(["eine Stunde", "eine Stunde 20", "40"])
    times = _format_cooking_time(recipe_time_column=series)
    pdt.assert_series_equal(times, pd.Series([60.0, 80.0, 40.0]))


def test_save_ingredients(monkeypatch, cleaned_recipes):
    mock = Mock()
    monkeypatch.setattr("data_ingestion.cleaning.df_to_sql", mock)
    save_ingredients(cleaned_recipes)
    mock.assert_called_once_with(ref="ingredients", df=ANY)
