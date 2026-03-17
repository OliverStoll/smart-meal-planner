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
