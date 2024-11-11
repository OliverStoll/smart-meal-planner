import ast
import json
import pandas as pd
import re


def filter_for_only_unique_recipes(df: pd.DataFrame) -> pd.DataFrame:
    """ get unique titles, and merge categories. keep other columns intact """
    other_columns = [col for col in df.columns if col not in ['title', 'category']]
    agg_dict = {col: 'first' for col in other_columns}
    agg_dict['category'] = lambda x: list(set((x)))
    df_grouped = df.groupby('title').agg(agg_dict).reset_index()
    return df_grouped


def clean_time_to_int(df: pd.DataFrame) -> pd.DataFrame:
    """ clean 'eine Stunde' in the time columns, by removing it and adding 60 minutes """
    time_columns = ['total_time', 'preparation_time']
    for idx, row in df.iterrows():
        for col in time_columns:
            if 'eine Stunde' in row[col]:
                try:
                    df.at[idx, col] = int(row[col].replace('eine Stunde', '')) + 60
                except Exception as e:
                    print(f"Error in row {idx}: {e}")
                    df.at[idx, col] = 60
    return df


class DataCleaner:
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
    replace_instruction_strings_re = {
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
        # 'Tortilla-Wraps (klein)': 'Tortilla-Wraps',
        'junger Gounda, gerieben': 'geriebener Gouda',
        'würziger Gouda, gerieben': 'geriebener würziger Gouda',
        'Großgarnelen': 'Garnelen',
        'Kirschtomaten (Dose)': 'Kirschtomaten',
        # 'lila Karotte': 'Karotte',
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

    }


    def clean_category_column(self, df) -> pd.DataFrame:
        """ make categories more readable """
        replace_strs = ['e-rezepte', 'e-gerichte', 's-rezepte', 'rezepte-', '-rezepte']
        for replace_str in replace_strs:
            df['category'] = df['category'].str.replace(replace_str, '')
        return df

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
    def _process_single_line(line):
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

    def _get_single_instructions(self, recipe_entry: pd.Series) -> list:
        instruction_steps = ast.literal_eval(recipe_entry["instructions"])
        for pattern in self.replace_instruction_strings_re:
            instruction_steps = [re.sub(pattern, '', x) for x in instruction_steps]
        for key, value in self.replace_instructions_strings.items():
            instruction_steps = [x.replace(key, value) for x in instruction_steps]
        instruction_steps = [x[2:].split('\n') for x in instruction_steps]
        final_instruction_steps = []
        for instruction_step in instruction_steps:
            instruction_step_lines = [line for line in instruction_step for line in self._process_single_line(line)]
            final_instruction_steps.append(instruction_step_lines)
        return final_instruction_steps

    def _get_single_ingredients(self, recipe_entry: pd.Series) -> list:
        try:
            for key, value in self.replace_ingredients_strings.items():
                recipe_entry["ingredients"] = recipe_entry["ingredients"].replace(key, value)
            ingredients = ast.literal_eval(recipe_entry["ingredients"])
            new_ingredients = []
            for ingredient in ingredients:
                if '/' in ingredient['name']:
                    split_quantity = int(int(ingredient['quantity']) / 2)
                    split_ingredient = {
                        'name': ingredient['name'].split('/')[1],
                        'quantity': split_quantity,
                        'unit': ingredient['unit']
                    }
                    ingredient['name'] = ingredient['name'].split('/')[0]
                    ingredient['quantity'] = split_quantity
                    new_ingredients.append(split_ingredient)
                    new_ingredients.append(ingredient)
                else:
                    new_ingredients.append(ingredient)
        except Exception as e:
            print(f"Error in row {recipe_entry['title']}: {e}")
            return []
        return new_ingredients

    def clean_instructions_column(self, df: pd.DataFrame) -> pd.DataFrame:
        df['instructions'] = df.apply(lambda x: self._get_single_instructions(x), axis=1)
        return df

    def clean_ingredients_column(self, df: pd.DataFrame) -> pd.DataFrame:
        df['ingredients'] = df.apply(lambda x: self._get_single_ingredients(x), axis=1)
        return df

    def clean_calories_column(self, df: pd.DataFrame) -> pd.DataFrame:
        # multiply all entries that contain kJ by 0.239006 and remove the kJ behind it
        df['calories'] = df['calories'].apply(lambda x: int(x[:-3]) * 0.239006 if 'kJ' in x else int(x))
        return df


    def clean_final_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """ apply all cleaning functions to the dataframe. Already expects unique recipes """
        df = self.clean_category_column(df)
        df = self.clean_instructions_column(df)
        df = self.clean_ingredients_column(df)
        df = self.clean_calories_column(df)
        df.rename(columns={'cooking_time': 'difficulty'}, inplace=True)
        return df


def list_all_ingredients(df: pd.DataFrame) -> pd.DataFrame:
    """ list all ingrediants in the dataframe """
    unique_ingredients_count = {}
    ingredients_entries = []
    for idx, row in df.iterrows():
        for ingredient in row['ingredients']:
            if ingredient['name'] in unique_ingredients_count:
                unique_ingredients_count[ingredient['name']] += 1
            else:
                unique_ingredients_count[ingredient['name']] = 1

    # print sorted
    unique_ingredients_count = {k: v for k, v in sorted(unique_ingredients_count.items(), key=lambda item: item[1], reverse=True)}
    old_ingredients_df = pd.read_csv('data/ingredients_v1.csv')
    for key, value in unique_ingredients_count.items():
        print(f"{value}: {key}")
        ingredients_entries.append({'name': key})
    ingredients_df = pd.DataFrame(ingredients_entries)
    # merge old where exists for category
    ingredients_df = pd.merge(ingredients_df, old_ingredients_df[['name', 'category']], on='name', how='left')
    print()
    # ingredients_df.to_csv('data/ingredients_v2.csv', index=False)


if __name__ == "__main__":
    df = pd.read_csv('data/uniques_v2.csv')
    df = DataCleaner().clean_final_data(df)
    list_all_ingredients(df)
    df.to_csv('data/cleaned_data_v2.csv', index=False)
    print()