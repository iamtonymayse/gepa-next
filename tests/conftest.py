import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Default to dev-mode auth bypass in tests unless overridden.
os.environ.setdefault("REQUIRE_AUTH", "false")
