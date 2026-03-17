import pandas as pd

from data_ingestion.cleaning import (
    remove_duplicate_recipes,
    remove_recipes_with_missing_data,
    clean_calories_column,
    clean_category_column,
    _process_single_instruction_line,
    _split_ingredient_entry,
)


class TestRemoveDuplicateRecipes:
    def test_removes_duplicate_ids(self):
        df = pd.DataFrame(
            {
                "id": ["1", "1", "2"],
                "link": ["a", "b", "c"],
                "title": ["T1", "T2", "T3"],
            }
        )
        result = remove_duplicate_recipes(df)
        assert len(result) == 2

    def test_removes_duplicate_links(self):
        df = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "link": ["a", "a", "c"],
                "title": ["T1", "T2", "T3"],
            }
        )
        result = remove_duplicate_recipes(df)
        assert len(result) == 2

    def test_removes_duplicate_titles(self):
        df = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "link": ["a", "b", "c"],
                "title": ["T1", "T1", "T3"],
            }
        )
        result = remove_duplicate_recipes(df)
        assert len(result) == 2

    def test_keeps_unique_recipes(self):
        df = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "link": ["a", "b", "c"],
                "title": ["T1", "T2", "T3"],
            }
        )
        result = remove_duplicate_recipes(df)
        assert len(result) == 3


class TestRemoveRecipesWithMissingData:
    def test_removes_rows_with_null_ingredients(self):
        df = pd.DataFrame(
            {
                "ingredients": ["[a]", None, "[b]"],
                "instructions": ["[i]", "[j]", "[k]"],
                "title": ["T1", "T2", "T3"],
            }
        )
        result = remove_recipes_with_missing_data(df)
        assert len(result) == 2

    def test_removes_rows_with_null_instructions(self):
        df = pd.DataFrame(
            {
                "ingredients": ["[a]", "[b]", "[c]"],
                "instructions": [None, "[j]", "[k]"],
                "title": ["T1", "T2", "T3"],
            }
        )
        result = remove_recipes_with_missing_data(df)
        assert len(result) == 2

    def test_removes_rows_with_null_title(self):
        df = pd.DataFrame(
            {
                "ingredients": ["[a]", "[b]", "[c]"],
                "instructions": ["[i]", "[j]", "[k]"],
                "title": ["T1", None, "T3"],
            }
        )
        result = remove_recipes_with_missing_data(df)
        assert len(result) == 2

    def test_keeps_all_rows_when_no_missing_data(self):
        df = pd.DataFrame(
            {
                "ingredients": ["[a]", "[b]"],
                "instructions": ["[i]", "[j]"],
                "title": ["T1", "T2"],
            }
        )
        result = remove_recipes_with_missing_data(df)
        assert len(result) == 2


class TestCleanCaloriesColumn:
    def test_converts_kj_to_kcal(self):
        df = pd.DataFrame({"calories": ["2000 kJ"]})
        result = clean_calories_column(df)
        expected = int(2000 * 0.239006)
        assert result["calories"].iloc[0] == expected

    def test_keeps_kcal_values_unchanged(self):
        df = pd.DataFrame({"calories": ["500"]})
        result = clean_calories_column(df)
        assert result["calories"].iloc[0] == 500

    def test_handles_numeric_values(self):
        df = pd.DataFrame({"calories": ["invalid"]})
        result = clean_calories_column(df)
        print(result)


class TestCleanCategoryColumn:
    def test_creates_category_friendly_column(self):
        df = pd.DataFrame({"category": ["vegetarische-rezepte"]})
        result = clean_category_column(df)
        assert "category_friendly" in result.columns

    def test_removes_rezepte_suffix(self):
        df = pd.DataFrame({"category": ["schnelle-rezepte"]})
        result = clean_category_column(df)
        assert "rezepte" not in result["category_friendly"].iloc[0]

    def test_removes_rezepte_prefix(self):
        df = pd.DataFrame({"category": ["rezepte-sommer"]})
        result = clean_category_column(df)
        assert result["category_friendly"].iloc[0] == "sommer"


class TestProcessSingleInstructionLine:
    def test_splits_line_on_period(self):
        line = "Heat the pan. Add oil"
        result = _process_single_instruction_line(line)
        assert len(result) == 2

    def test_strips_whitespace(self):
        line = "  Heat the pan  "
        result = _process_single_instruction_line(line)
        assert all(s == s.strip() for s in result)

    def test_returns_list(self):
        line = "Simple instruction"
        result = _process_single_instruction_line(line)
        assert isinstance(result, list)

    def test_filters_short_lines(self):
        line = "A."
        result = _process_single_instruction_line(line)
        assert all(len(item) > 3 for item in result)


class TestFormatInstructionMeasurement:
    def test_formats_measurement_with_unit(self):
        text = "Add 200 g [200 g Mehl]"
        result = _process_single_instruction_line(text)
        assert "[200 g]" in result[0]

    def test_formats_measurement_without_unit(self):
        text = "Add 5 [5 Stücke]"
        result = _process_single_instruction_line(text)
        assert "[5]" in result[0]

    def test_returns_unchanged_text_without_pattern(self):
        text = "Simply cook until done."
        result = _process_single_instruction_line(text)
        assert result[0] == text


class TestSplitIngredientEntry:
    def test_splits_paired_ingredient(self):
        ingredient = {"name": "Tomate/Paprika", "quantity": "4", "unit": "Stück"}
        first, second = _split_ingredient_entry(ingredient)
        assert first["name"] == "Tomate"
        assert second["name"] == "Paprika"

    def test_splits_quantity_in_half(self):
        ingredient = {"name": "Apfel/Birne", "quantity": "4", "unit": "Stück"}
        first, second = _split_ingredient_entry(ingredient)
        assert first["quantity"] == 2
        assert second["quantity"] == 2

    def test_preserves_unit(self):
        ingredient = {"name": "Käse/Tofu", "quantity": "200", "unit": "g"}
        first, second = _split_ingredient_entry(ingredient)
        assert first["unit"] == "g"
        assert second["unit"] == "g"
