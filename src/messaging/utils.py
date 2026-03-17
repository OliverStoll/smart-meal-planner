from database.engine import recipes_from_sql
from messaging import CALLBACK_DELIM


def get_pdf_title_from_meal_name(meal_name: str) -> str:
    pdf_title = meal_name.replace(":", "").replace("!", "").replace("&", "und")
    return pdf_title


def str_to_int(value: str):
    try:
        value = int(value)
    except ValueError:
        pass
    return value


def callback_str(values: list[str] | str) -> str:
    if isinstance(values, str):
        values = [values]
    return CALLBACK_DELIM.join(str(values))


def id_to_title(recipe_id: int) -> str:
    recipes = recipes_from_sql()
    row = recipes.loc[recipes["id"] == recipe_id, "title"]
    return row.iloc[0] if not row.empty else None
