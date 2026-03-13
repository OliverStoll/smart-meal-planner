import ast
from data_ingestion.cleaning import DataCleaner


class TestDataCleaning:
    cleaner = DataCleaner()

    def test_clean_recipes_data(self, raw_recipes_df):
        self.cleaner.clean_recipes_data(raw_recipes_df)
        assert "ingredients" in raw_recipes_df.columns, "Expected 'ingredients' column after cleaning"
        assert "instructions" in raw_recipes_df.columns, "Expected 'instructions' column after cleaning"
        assert (
            raw_recipes_df["ingredients"].apply(lambda x: isinstance(ast.literal_eval(x), list)).any()
        ), "Expected 'ingredients' to be a list"
        assert (
            raw_recipes_df["instructions"].apply(lambda x: isinstance(ast.literal_eval(x), list)).any()
        ), "Expected 'instructions' to be a list"
