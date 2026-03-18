from typing import Literal
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from logs.logs import create_logger
from cachetools import TTLCache, cached

from settings import PROJECT_NAME, DATABASE_URL, CACHE_DURATION_HOURS
from database import CLEANED_RECIPES_REF

load_dotenv()

log = create_logger("Database")
_cache = TTLCache(maxsize=1024, ttl=CACHE_DURATION_HOURS * 3600)

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except Exception:
    log.error("DB Engine was not initialized")
    engine = None


def _table_name(table_name: str):
    """Prefix the table name with the project name to avoid conflicts in shared databases."""
    return f"{PROJECT_NAME}-{table_name}"


@cached(_cache)
def _fetch_table(ref) -> pd.DataFrame:
    df = pd.read_sql_table(table_name=_table_name(ref), con=engine)
    log.debug(f"Loaded table {ref} from SQL")
    return df


def df_from_sql(ref: str) -> pd.DataFrame | None:
    try:
        return _fetch_table(ref=ref)
    except Exception:
        log.error(f"Could not load {ref} from SQL")
        return None


def df_to_sql(
    df: pd.DataFrame,
    ref: str,
    if_exists: Literal["fail", "replace", "append"] = "replace",
    dtype=None,
):
    try:
        df.to_sql(_table_name(ref), con=engine, if_exists=if_exists, index=False, dtype=dtype)
        log.debug(f"Stored table {ref} to SQL")
    except Exception:
        log.error(f"Could not store {ref} to SQL")


def recipes_from_sql() -> pd.DataFrame | None:
    return df_from_sql(ref=CLEANED_RECIPES_REF)
