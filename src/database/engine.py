from dotenv import load_dotenv
from sqlalchemy import create_engine
import os

from config.settings import PROJECT_NAME

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def table(table_name: str):
    """Prefix the table name with the project name to avoid conflicts in shared databases."""
    return f"{PROJECT_NAME}-{table_name}"
