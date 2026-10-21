"""Keep disposable test files within the explicitly writable workspace."""
from pathlib import Path
import tempfile
_test_root = Path(__file__).resolve().parents[1] / 'work' / 'test_tmp'
_test_root.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_test_root)
