import os
from pathlib import Path

# Set DOCKER_WORKDIR so common_utils can resolve the project ROOT_DIR
os.environ.setdefault("DOCKER_WORKDIR", str(Path(__file__).parent.parent))

# Provide a dummy Firebase URL so modules with class-level FirebaseClient
# attributes can be imported without real credentials during testing.
os.environ.setdefault("FIREBASE_REALTIME_DB_URL", "https://test-default-rtdb.firebaseio.com")
