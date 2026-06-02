import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault(
    "AUTOMATION_GOOGLE_CREDENTIALS",
    str(Path(__file__).resolve().with_name("credentials.json")),
)

from core.google_logger import GoogleSheetLogger
