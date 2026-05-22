import os
import sys
from pathlib import Path

# Ensure backend app is importable
BASE = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BASE))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")