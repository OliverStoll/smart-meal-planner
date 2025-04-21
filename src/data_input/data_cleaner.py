import ast
import json
import pandas as pd
import re

from utils.logger import create_logger
from utils.config import ROOT_DIR


class DataCleaner:
    log = create_logger('DataCleaner')
    output_path = 'data/temp_data/cleaned.csv'
    replace_instructions_strings = {
        'Min.': 'Min',
        'Ca.': 'Ca',
        'ca.': 'ca',
        'Sek.': 'Sek',
        'Std.': 'Std',
        'sek.': 'sek',
        'std.': 'std',
        'min.': 'min',
        'gestr.': '',
        ' – ': '-',
        '–': '-',
        '„Hello ': 'Gewürzmischung "',
        '“': '"',
        '„': '"',
        '*': '',
        'gesamte [drei Viertel | gesamte]': 'gesamte',
        'ein Viertel [ein Drittel | ein Drittel]': 'ein Viertel',
        'Ein Viertel [ein Sechstel | ein Achtel]': 'ein Viertel',
        'Guten Appetit!': '',
        'Hälfte ': 'HÄLFTE ',
        'ein Drittel ': 'EIN DRITTEL ',
        'zwei Drittel ': 'ZWEI DRITTEL ',
        'ein Viertel ': 'EIN VIERTEL ',
        'drei Viertel ': 'DREI VIERTEL ',
    }
    replace_instruction_patterns = {
        r'Hälfte \[.*?\]': '',
        r'halben \[.*?\]': '',
        r'halbe \[.*?\]': '',
        r'(\d)\.(\d)': r'\1.\2',
    }
    replace_ingredients_strings = {
        ', Bio': '',
        'Bio ': '',
        'Hello ': '',
        '„': '"',
        '“': '"',
        'frische ': '',
        'frischer ': '',
        'Hartkäse ital. Art, gerieben': 'Parmesan',
        'Hartkäse ital. Art, geraspelt': 'Parmesan',
        ', gewachst': '',
        ', vegan': '',
        ', natur': '',
        '(Premium)': '',
        'Kochsahne': 'Sahne',
        'Gemüsebrühpulver': 'Gemüsebrühe',
        'Naturjogurt': 'Joghurt',
        'Naturjoghurt': 'Joghurt',
        'mittelscharfer Senf': 'Senf',
        'rote Chilischote': 'Chilischote',
        'Paprika multicolor': 'Paprika',
        'rote Spitzpaprika': 'Paprika',
        'Basmatireis': 'Reis',
        'Jasminreis': 'Reis',
        'kleine Salatgurke': 'Gurke',
        ' in Lake': '',
        ', glatt': '',
        ' glatt': '',
        'Weizentortillas': 'Tortilla-Wraps',
        'rote Paprika': 'Paprika',
        'gelbe Paprika': 'Paprika',
        'stückige Tomaten': 'Tomaten',
        'rote Kirschtomaten': 'Kirschtomate',
        'Rinderhackfleischzubereitung': 'Rinderhackfleisch',
        'gemischte Hackfleischzubereitung': 'gemischtes Hackfleisch',
        'geriebener Hartkäse': 'Parmesan',
        'Libanesisches Fladenbrot': 'Fladenbrot',
        ' ohne Schale': '',
        'Blütenhonig': 'Honig',
        'Hähnchengeschnetzeltes, mariniert': 'Hähnchengeschnetzeltes',
        'Bacon (Scheiben)': 'Bacon',
        'Buttermilch-Zitronen-Dressing': 'Zitronen-Buttermilch',
        'Hartkäse geraspelt': 'Parmesan',
        'friche Linguine': 'Linguine',
        'Grillkäse Zypriotischer Art': 'Grillkäse',
        'Halloumi': 'Grillkäse',
        'Quinoa Tri-Color': 'Quinoa',
        'Weizenmehl': 'Mehl',
        'Tomate (Roma)': 'Tomate',
        'Skipjack Thunfisch': 'Thunfisch',
        ' im eigenen Saft': '',
        'junger Gounda, gerieben': 'geriebener Gouda',
        'würziger Gouda, gerieben': 'geriebener würziger Gouda',
        'Großgarnelen': 'Garnelen',
        'Kirschtomaten (Dose)': 'Kirschtomate',
        'lila Karotte': 'Karotte',
        'Getrocknete Tomaten mit Kräutern': 'Getrocknete Tomaten',
        'Wildpreiselbeeren': 'Preiselbeer',
        'und gehobelte Karotten': '& Karotten',
        'veganes cremiges Sojaprodukt': 'vegane Sahne',
        'Knoblauch & Zwiebel gehackt in Rapsöl': 'Knoblauch & Zwiebel',
        'gehackter Knoblauch & Ingwer in Öl': 'Knoblauch & Ingwer',
        'Gehackte Tomaten mit Knoblauch und Zwiebeln': 'Tomaten, Knoblauch & Zwiebeln',
        'Marinierter Tofu mit Basilikum': 'Marinierter Tofu',
        'Hähncheninnenbrustfilet': 'Hähnchenbrustfilet',
        'vegane Brioche Burger Buns': 'Burger Buns',
        'Basmati-Wildreis-Mischung': 'Basmati-Wildreis',
        'Simmentaler ': '',
        'Hähnchenkeule in Kräutermarinade': 'Hähnchenkeule mariniert',
        'Beyond Meat ': '',
        'GREENFORCE ': '',
        'veganer ': '',
        'vegane ': '',
        'veganes ': '',
        'Veganer ': '',
        'Vegane ': '',
        'Veganes ': '',
        'braune Champignons': 'Champignons',
        ', ungewachst': '',
        ', vorgeschnitten': '',
        'TABASCO®': 'Tabasco',
        'Premium ': '',
        'The Vegetarian Butcher ': '',
        'Fleischtomate': 'Tomate',
        'rosa ': '',
        'orange Paprika': 'Paprika',
        'Paprika, orange': 'Paprika',
        'Kindercurry': 'Curry',
        'Bunte Karotten': 'Karotten',
        'schwarze Oliven (mit Stein)': 'schwarze Oliven',
        'Arborio-Reis': 'Risotto-Reis',
        'große Tomate': 'Tomate',
        'Rauchsalz': 'Salz',
        'Sonnenflocken - Grobes Meersalz': 'Salz',
        ' von Vivera': '',
        'Polpa Chili': 'Chili',
        'Ochsenherztomaten': 'Tomate',
        'weiße / braune Bohnen': 'weiße Bohnen',
        'gelbe Chilischote': 'Chilischote',
        'Schweineschnitzel': 'Schnitzel',
        'SalaRico®': 'Salat',
        "Tony's Chocolonely ": '',
        'Seelachs ohne Haut': 'Seelachs',
        'Champignons in Scheiben': 'Champignons',
        'frisches Lorbeerblatt': 'Lorbeerblatt',
        'dunkles Ciabatta-Brötchen': 'Ciabatta-Brötchen',
        'gelbe Kirschtomaten': 'Kirschtomate',
        'Planted ': '',
        'Briochebrötchen mit Sesam': 'Briochebrötchen',
        'hartgekochte Eier': 'Eier',
        'Eiertomaten': 'Tomate',
        'Mehrkornbaguette': 'Baguette',
        'rote Frühlingszwiebeln': 'Frühlingszwiebeln',
        'Chinakohl, vorgeschnitten': 'Chinakohl',
        'roter Rettich': 'Rettich',
        'Baby-Mais': 'Mais',
        'Blumenkohl-Reis': 'Reis',
        'Mildes Sauerkraut': 'Sauerkraut',
        'Karotte gelb und orange, geschnitten': 'Karotte',
        'Brokkoli-Reis': 'Reis',
        'Himbeertomate': 'Tomate',
        'gemahlener Zimt': 'Zimt',
        'gemahlener Piment': 'Piment',
        'Haselnussspätzle': 'Spätzle',
        'Bulgur, vorgekocht und gesalzen': 'Bulgur',
        'Knoblauch & Zwiebel': 'Knoblauchzehe / Zwiebel',
        'Butterbohnen': 'grüne Bohnen',
        'Prinzessbohnen': 'grüne Bohnen',
        'Hähnchenbrustfilet': 'Hähnchenbrust',
        'Hähncheninnenfilets': 'Hähnchenbrust',
        'Tortilla-Wraps': 'Wraps',
        # 'Tomaten': 'Tomate',
        'Kirschtomaten': 'Kirschtomate',
        'veganer Brioche Burger Bun': 'Burger Buns',
        'veganer Brioche Bun': 'Burger Buns',
        'Brioche Bun': 'Burger Buns',
        'saure Sahne': 'Sahne',
        'Sahne leicht': 'Sahne',
        'vegane Sahne': 'Sahne',
        'Schlagsahne': 'Sahne',
        'Aprikosenchutney': 'Aprikosen-Marmelade',
        'Aprikosenkonfitüre': 'Aprikosen-Marmelade',
        'Tomatensugo': 'Tomatensauce',
        'Tomatesugo': 'Tomatensauce',
        'gemahlener Kumin': 'Kreuzkümmel',
        'Sesamsamen': 'Sesam',
        'Basmati-Wildreis': 'Reis',
        'Hokkaido-Kürbis': 'Kürbis',
        'Norwegisches ': '',
       #  ' Zwiebel': 'Zwiebel',
        'milder Chili-Mix': 'Chili',
        'Chili-Nudeln': 'Nudeln',
        'milde Chiliflocken': 'Chili',
        'Perlencouscous': 'Couscous',
        'Paprika (rot, gelb oder orange)': 'Paprika',
        'getrocknete Tomate': 'Getrocknete Tomate',
        'Kürbis, geschält und gewürfelt': 'Kürbis',
        'Sultaninen': 'Rosinen',
        'gerebelter Thymian': 'Thymian',
        'grüne Chilischote': 'Chilischote',
        'Steinofenbaguette (Inhalt: 250 g)': 'Baguette',
        'Parmesan D.O.P.': 'Parmesan',
        'Zwiebeln': 'Zwiebel',

    }

    def __init__(self):
        pass

    def clean_recipes_data(self, recipes: pd.DataFrame) -> pd.DataFrame:
        """ apply all cleaning functions to the dataframe. Already expects unique recipes """
        recipes = self.remove_duplicates(recipes)
        recipes = self.remove_recipes_with_missing_data(recipes)

        recipes = self.clean_category_column(recipes)
        recipes = self.clean_instructions_column(recipes)
        recipes = self.clean_ingredients_column(recipes)
        recipes = self.clean_calories_column(recipes)
        recipes['total_time'] = self.format_cooking_time(recipes['total_time'])
        recipes.rename(columns={'cooking_time': 'difficulty'}, inplace=True)
        return recipes

    def remove_duplicates(self, recipes: pd.DataFrame) -> pd.DataFrame:
        """ Remove all duplicate recipes, identified by id """
        recipes = recipes.drop_duplicates(subset=['id'], keep='first')
        recipes = recipes.drop_duplicates(subset=['link'], keep='first')
        recipes = recipes.drop_duplicates(subset=['title'], keep='first')
        return recipes

    def remove_recipes_with_missing_data(self, recipes: pd.DataFrame) -> pd.DataFrame:
        """ Remove recipes with missing data in the ingredients or instructions columns """
        recipes = recipes[recipes['ingredients'].notnull()]
        recipes = recipes[recipes['instructions'].notnull()]
        recipes = recipes[recipes['title'].notnull()]
        return recipes

    def clean_instructions_column(self, df: pd.DataFrame) -> pd.DataFrame:
        df['instructions'] = df.apply(lambda row: self._get_recipe_instructions(row), axis=1)
        return df

    def _get_recipe_instructions(self, recipe_entry: pd.Series, first_steps_to_ignore: int = 2) -> list[list[str]]:
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
        for replace_pattern, replace_value in self.replace_instruction_patterns.items():
            instruction_steps = [re.sub(replace_pattern, replace_value, x) for x in instruction_steps]
        for replace_str, replace_value in self.replace_instructions_strings.items():
            instruction_steps = [x.replace(replace_str, replace_value) for x in instruction_steps]
        instruction_steps = [x[first_steps_to_ignore:].split('\n') for x in instruction_steps]

        all_instruction_lines = []
        for instruction_step in instruction_steps:
            instruction_step_lines = []
            for line in instruction_step:
                instruction_step_lines += self._process_single_instruction_line(line)
            all_instruction_lines.append(instruction_step_lines)

        return all_instruction_lines

    def clean_ingredients_column(self, recipes: pd.DataFrame) -> pd.DataFrame:
        recipes['ingredients'] = recipes.apply(lambda x: self._clean_recipe_ingredients(x), axis=1)
        return recipes

    def _clean_recipe_ingredients(self, recipe_entry: pd.Series) -> list[dict]:
        """
        Clean the ingredients column by replacing certain strings and splitting paired ingredients.

        Args:
            recipe_entry: A single recipe entry from the dataframe.

        Returns:
            A list of cleaned ingredient entries with 'name', 'quantity', and 'unit' keys.
        """
        if not recipe_entry["ingredients"]:
            self.log.warning(f"No ingredients found for recipe: {recipe_entry['title']}")
            return []

        for key, value in self.replace_ingredients_strings.items():
            recipe_entry["ingredients"] = recipe_entry["ingredients"].replace(key, value)
            recipe_entry["ingredients"] = recipe_entry["ingredients"].strip()

        try:
            ingredient_entries = ast.literal_eval(recipe_entry["ingredients"])
            cleaned_ingredients = self._split_all_paired_ingredients(ingredient_entries)
        except Exception as e:
            print(f"Error in cleaning ingredients for {recipe_entry['title']}: {e}")
            return []

        return cleaned_ingredients

    def _split_all_paired_ingredients(self, ingredients_entries: list[dict]) -> list[dict]:
        """
        Split all ingredients that are paired with a '/' into two separate entries.

        Args:
            ingredients_entries: A list of ingredient entries, each entry is a dictionary with 'name', 'quantity', and 'unit'.

        Returns:
            A list of ingredient entries with 'name', 'quantity', and 'unit' keys, where all ingredients are split.
        """
        cleaned_ingredients = []
        for ingredient_entry in ingredients_entries:
            if '/' in ingredient_entry['name']:
                first_ingredient, second_ingredient = self._split_ingredient_entry(ingredient_entry)
                cleaned_ingredients.append(first_ingredient)
                cleaned_ingredients.append(second_ingredient)
            else:
                cleaned_ingredients.append(ingredient_entry)

        return cleaned_ingredients

    @staticmethod
    def _split_ingredient_entry(ingredient: dict) -> tuple[dict, dict]:
        split_quantity = int(int(ingredient['quantity']) / 2)
        split_ingredient = {
            'name': ingredient['name'].split('/')[1],
            'quantity': split_quantity,
            'unit': ingredient['unit']
        }
        ingredient['name'] = ingredient['name'].split('/')[0]
        ingredient['quantity'] = split_quantity
        return ingredient, split_ingredient

    @staticmethod
    def clean_calories_column(recipes: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the calories column by removing the kJ and converting to kcal.
        """
        def convert_calories(calories_str: str) -> int:
            if 'kJ' in calories_str:
                return int(int(calories_str[:-3]) * 0.239006)
            else:
                return int(calories_str)

        recipes['calories'] = recipes['calories'].apply(lambda x: convert_calories(x) if isinstance(x, str) else x)
        return recipes

    @staticmethod
    def clean_category_column(recipes: pd.DataFrame) -> pd.DataFrame:
        """ make categories more readable """
        strs_to_remove = ['e-rezepte', 'e-gerichte', 's-rezepte', 'rezepte-', '-rezepte']
        recipes['category_friendly'] = recipes['category']
        for replace_str in strs_to_remove:
            recipes['category_friendly'] = recipes['category_friendly'].str.replace(replace_str, '')
        return recipes

    @staticmethod
    def _process_single_instruction_line(line):
        line = line.strip()
        if line.endswith('.'):
            line = line[:-1]
        if '.' in line:
            split_lines = [x.strip() + '.' for x in line.split('.')]
        else:
            split_lines = [line.strip() + '.']
        split_lines = [x for x in split_lines if len(x) > 3]
        split_lines = [DataCleaner._format_instruction_measurement(x) for x in split_lines]
        return split_lines

    @staticmethod
    def _format_instruction_measurement(text):
        pattern = r"(\d+(?:,\d+)?)\s*(\w*)\s*\[.*?\]"

        def replacer(match):
            number = match.group(1)
            unit = match.group(2).strip()  # Handle case when there's no unit
            return f'[{number} {unit}]' if unit else f'[{number}]'
        new_text = re.sub(pattern, replacer, text)
        return new_text

    @staticmethod
    def format_cooking_time(
            recipe_time_column: pd.Series,
    ) -> pd.Series:
        """ clean 'eine Stunde' in the time columns, by removing it and adding 60 minutes """
        def convert_time_to_minutes(time_str: str) -> int:
            if 'eine Stunde' in time_str:
                time_str = time_str.replace('eine Stunde', '').strip()
                remaining_time = int(time_str) if time_str else 0
                return remaining_time + 60
            else:
                return int(time_str)

        recipe_time_column = recipe_time_column.apply(lambda x: convert_time_to_minutes(x) if isinstance(x, str) else x)
        return recipe_time_column


def list_all_ingredients(df: pd.DataFrame, output_path: str | None = None) -> pd.DataFrame:
    """ list all ingrediants in the dataframe """

    unique_ingredients_count = {}
    ingredients_entries = []
    for idx, row in df.iterrows():
        for ingredient in row['ingredients']:
            name = ingredient['name']
            unique_ingredients_count[name] = unique_ingredients_count.get(name, 0) + 1

    # print sorted
    unique_ingredients_count = {
        k: v for k, v in sorted(unique_ingredients_count.items(), key=lambda item: item[1], reverse=True)
    }

    for name, count in unique_ingredients_count.items():
        print(f"{count}: {name}")
        ingredients_entries.append({'name': name})

    ingredients_df = pd.DataFrame(ingredients_entries)
    old_ingredients_df = pd.read_csv(f'{ROOT_DIR}/data/recipes/ingredients_v2.csv')
    ingredients_df = pd.merge(ingredients_df, old_ingredients_df[['name', 'category']], on='name', how='left')

    if output_path:
        ingredients_df.to_csv(output_path, index=False)



if __name__ == "__main__":
    output_path = f'{ROOT_DIR}/data/temp_data/cleaned.csv'
    df = pd.read_csv(f'{ROOT_DIR}/data/temp_data/recipes.csv')
    df = DataCleaner().clean_recipes_data(df)
    df.to_csv(output_path, index=False)
    list_all_ingredients(df, output_path=f'{ROOT_DIR}/data/temp_data/ingredients.csv')
    print()