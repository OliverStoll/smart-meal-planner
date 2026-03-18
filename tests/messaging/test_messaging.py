from messaging.messaging import replace_single_recipe_in_data


def test_replace_single_recipe_in_data(cleaned_recipes, monkeypatch):
    monkeypatch.setattr("messaging.recipes.recipes_from_sql", lambda *_: cleaned_recipes)
    last_sent_recipes, idx_to_replace = replace_single_recipe_in_data(
        recipes=cleaned_recipes, chat_id=123, recipe_id=cleaned_recipes.iloc[0]["id"]
    )
    assert idx_to_replace == 0
