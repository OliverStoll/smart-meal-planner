from typing import Literal
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
import diskcache as dc
from common_utils.logger import create_logger

from config.settings import PROJECT_NAME, DATABASE_URL, CACHE_DURATION_HOURS
from database import CLEANED_RECIPES_REF

load_dotenv()

log = create_logger("Database")
cache = dc.Cache(".cache_sql")

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except Exception:
    log.error("DB Engine was not initialized")
    engine = None


def _table_name(table_name: str):
    """Prefix the table name with the project name to avoid conflicts in shared databases."""
    return f"{PROJECT_NAME}-{table_name}"


@cache.memoize(expire=CACHE_DURATION_HOURS * 3600)
def _fetch_table(ref):
    df = pd.read_sql_table(table_name=_table_name(ref), con=engine)
    log.debug(f"Loaded table {ref} from SQL")
    return df


def df_from_sql(ref: str):
    try:
        _fetch_table(ref=ref)
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
        df.to_sql(
            _table_name(ref), con=engine, if_exists=if_exists, index=False, dtype=dtype
        )
        log.debug(f"Stored table {ref} to SQL")
    except Exception:
        log.error(f"Could not store {ref} to SQL")


def recipes_from_sql():
    return df_from_sql(ref=CLEANED_RECIPES_REF)
