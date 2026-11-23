import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

# example models (examples/systems) are tested too: their analytical Jacobians
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
