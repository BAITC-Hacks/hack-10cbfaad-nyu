import sys
from pathlib import Path


# Allow pytest to import the service package when tests are started from the
# repository root or from the ai-service directory.
SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
