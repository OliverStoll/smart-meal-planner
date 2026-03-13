from common_utils.apis.firebase import FirebaseClient
from common_utils.logger import create_logger

log = create_logger("NoSQL DB")


def nosql_client(realtime_db_url: str):
    try:
        return FirebaseClient(realtime_db_url=realtime_db_url)
    except Exception:
        log.error("Error initializing Firebase Client")
        return None
