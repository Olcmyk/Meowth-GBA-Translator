"""Helper to get resource paths in both dev and PyInstaller environments."""

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and PyInstaller.

    Args:
        relative_path: Path relative to project root (e.g., "Pokemon_GBA_Font_Patch/pokeFRLG")

    Returns:
        Absolute path to the resource
    """
    if getattr(sys, '_MEIPASS', None):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent.parent

    return base_path / relative_path
