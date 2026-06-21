"""Make `kbscraper` importable in tests without an install (src layout)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
