import os

PROJECT_NAME = os.getenv("PROJECT_NAME", "meal_bot")
RECIPE_URL = os.getenv("RECIPE_URL", "https://www.hellofresh.de/recipes/")
DATABASE_URL = os.getenv("DATABASE_URL")
CACHE_DURATION_HOURS = int(os.getenv("CACHE_DURATION_HOURS", "24"))
REALTIME_DB_URL = os.getenv("FIREBASE_REALTIME_DB_URL")
NOSQL_BASE_REF = "AppData/Telegram Meal Bot"
NOSQL_USER_DATA_REF = NOSQL_BASE_REF + "/User Settings"
NOSQL_FAVORITES_REF = NOSQL_BASE_REF + "/Favorites"
NOSQL_SUBSCRIPTION_REF = NOSQL_BASE_REF + "/Subscriptions"
BUCKET_REF = "meal-bot"
DEBUG = os.getenv("DEBUG", True)
RESTART_TIME = 10
