from messaging.ingredients import ingredients_shopping_list


def test_ingredients_shopping_list(cleaned_recipes):
    shopping_list = ingredients_shopping_list(recipes=cleaned_recipes, num_portions=1)
    assert "  1    Baguette" in shopping_list
    assert "0.5 Pk braune Linsen" in shopping_list
