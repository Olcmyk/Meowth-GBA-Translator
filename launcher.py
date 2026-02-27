"""PyInstaller entry point for Meowth GUI app."""
import sys
from pathlib import Path

# Ensure src/ is on the path so meowth package can be found
src_dir = Path(__file__).parent / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

from meowth.gui.app import main

if __name__ == "__main__":
    main()
