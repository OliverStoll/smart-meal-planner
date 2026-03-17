from messaging.callbacks.settings_types import SettingsProperties

CALLBACK_DELIM = "|"
QUANTITY_REPLACE_MAP: dict[str, str] = {
    "½": "0.5",
    "¼": "0.25",
    "¾": "0.75",
    "⅓": "0.333",
    "⅔": "0.667",
    "⅕": "0.2",
    "⅛": "0.125",
    "⅜": "0.375",
    "⅝": "0.625",
    "⅞": "0.875",
}
UNIT_REPLACE_MAP = {
    "Stück": "",
    "Packung": "Pk",
}

MESSAGE_SETTING_CONFIGS: dict[str, SettingsProperties] = {
    "portions": SettingsProperties(
        name="portions",
        friendly_name="Portionsanzahl",
        options=[1, 2, 3, 4, 5, 6],
        default_value=2,
        query_message="🍽️ Wähle die Anzahl der Portionen pro Gericht:",
        confirmation_message="🍽️ Du erhältst jetzt Rezepte für {value} Portionen.",
    ),
    "meal_type": SettingsProperties(
        name="meal_type",
        friendly_name="Art der Gerichte",
        options=["alle", "vegetarisch", "vegan", "protein"],
        default_value="alle",
        query_message="🥗 Wähle die Art der Gerichte:",
        confirmation_message="🥗 Du erhältst jetzt {value} Gerichte.",
        option_labels={
            "alle": "alle",
            "vegetarisch": "vegetarische",
            "vegan": "vegane",
            "protein": "proteinreiche",
        },
        is_filter=True,
    ),
    "max_duration": SettingsProperties(
        name="max_duration",
        friendly_name="Kochzeit",
        options=[10, 15, 20, 25, 30, 45, 60, 90],
        default_value=120,
        query_message="⏱️ Wähle die maximale Kochzeit (in Minuten):",
        confirmation_message="⏱️ Deine maximale Kochzeit beträgt {value} Minuten.",
        is_filter=True,
    ),
    "cal_min": SettingsProperties(
        name="cal_min",
        friendly_name="Kalorien (min.)",
        options=[0, 500, 600, 700, 800, 900],
        default_value=0,
        query_message="🔥 Wähle die minimalen Kalorien pro Portion:",
        confirmation_message="🔥 Du erhältst jetzt Gerichte mit mindestens {value} kcal pro Portion.",
        is_filter=True,
    ),
}

# TODO: settings
home_ingredients = [
    "milder Chili-Mix",
    "Gewürzmischung",
    "zwiebel",
    "schalotte",
    "knoblauch",
    "ketchup",
    "mayonnaise",
    "sojasoße",
    "tomatenmark",
    "gemüsebrüh",
    "piment",
    "senf",
    "wasser",
    "Madras Curry",
    "Madras-Curry",
    "Schwarzkümmel",
]
category_order = [
    "Obst",
    "Gemüse",
    "Gewürze",
    "Brot",
    "Fleisch",
    "Haltbares",
    "Milchprodukte",
    "Verschiedenes",
]
