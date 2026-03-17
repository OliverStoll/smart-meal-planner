from threading import Lock
from common_utils.apis.firebase import FirebaseClient
from common_utils.logger import create_logger

from settings import REALTIME_DB_URL

log = create_logger("NoSQL DB")

_client = None
_lock = Lock()


def nosql_client():
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is None:
            _client = FirebaseClient(realtime_db_url=REALTIME_DB_URL)
    return _client
