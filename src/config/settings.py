import os
from pathlib import Path

from common_utils.config import ROOT_DIR

PROJECT_NAME = os.getenv("PROJECT_NAME", "meal_bot")
RECIPE_URL = os.getenv("RECIPE_URL", "https://www.hellofresh.de/recipes/")
ROOT_DIR = Path(ROOT_DIR)
