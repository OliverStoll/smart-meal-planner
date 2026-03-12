import os
from pathlib import Path

# Set DOCKER_WORKDIR so common_utils can resolve the project ROOT_DIR
os.environ.setdefault("DOCKER_WORKDIR", str(Path(__file__).parent.parent))
