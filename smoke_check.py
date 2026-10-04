from pathlib import Path
import importlib

ROOT=Path(__file__).parent
mods=["config","credit_engine","auth","storage","research"]
for m in mods:
    importlib.import_module(m)
import app  # noqa: F401
print("SMOKE TEST OK")
