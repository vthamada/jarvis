"""Shared pytest configuration for the repository."""

import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
TEMP_ROOT = Path(tempfile.gettempdir()) / f"jarvis-pytest-root-{uuid4().hex[:8]}"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(TEMP_ROOT))

SRC_DIRS = [
    ROOT,
    ROOT / "evolution" / "evolution-lab" / "src",
    ROOT / "services" / "orchestrator-service" / "src",
    ROOT / "services" / "memory-service" / "src",
    ROOT / "services" / "governance-service" / "src",
    ROOT / "services" / "operational-service" / "src",
    ROOT / "services" / "knowledge-service" / "src",
    ROOT / "services" / "observability-service" / "src",
    ROOT / "engines" / "identity-engine" / "src",
    ROOT / "engines" / "executive-engine" / "src",
    ROOT / "engines" / "cognitive-engine" / "src",
    ROOT / "engines" / "planning-engine" / "src",
    ROOT / "engines" / "synthesis-engine" / "src",
]

for src_dir in SRC_DIRS:
    sys.path.insert(0, str(src_dir))
