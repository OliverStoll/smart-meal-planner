from data_ingestion.cleaning import DataCleaner


class TestDataCleaning:
    cleaner = DataCleaner()

    def test_clean_recipes_data(self, raw_recipes):
        cleaned_recipes = self.cleaner.clean_recipes_data(raw_recipes)
        assert (
            "ingredients" in cleaned_recipes.columns
        ), "Expected 'ingredients' column after cleaning"
        assert (
            "instructions" in cleaned_recipes.columns
        ), "Expected 'instructions' column after cleaning"
        assert (
            cleaned_recipes["ingredients"].apply(lambda x: isinstance(x, list)).any()
        ), "Expected 'ingredients' to be a list"
        assert (
            cleaned_recipes["instructions"].apply(lambda x: isinstance(x, list)).any()
        ), "Expected 'instructions' to be a list"
