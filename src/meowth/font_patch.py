"""Apply Pokemon_GBA_Font_Patch via armips."""

import platform
import shutil
import subprocess
from pathlib import Path

from .resource_path import get_resource_path

_PATCH_ROOT = get_resource_path("Pokemon_GBA_Font_Patch")

# Select armips executable based on platform
_system = platform.system()
if _system == "Windows":
    DEFAULT_ARMIPS = get_resource_path("tools/armips.exe")
elif _system == "Darwin":
    DEFAULT_ARMIPS = get_resource_path("tools/armips")
else:  # Linux
    DEFAULT_ARMIPS = get_resource_path("tools/armips")

# Per-game configuration for the font patch
_GAME_CONFIG: dict[str, dict] = {
    "firered": {
        "subdir": "pokeFRLG",
        "asm": "main_FR.asm",
        "baserom": "baserom_FR.gba",
        "output": "chsfontrom_FR.gba",
        "use_strequ": False,
    },
    "leafgreen": {
        "subdir": "pokeFRLG",
        "asm": "main_FR.asm",
        "baserom": "baserom_FR.gba",
        "output": "chsfontrom_FR.gba",
        "use_strequ": False,
    },
    "emerald": {
        "subdir": "pokeE",
        "asm": "main_E.asm",
        "baserom": "baserom_E.gba",
        "output": "baserom_E_chs.gba",
        "use_strequ": True,
    },
}


def apply_font_patch(
    rom_path: Path,
    output_path: Path,
    armips_path: Path = DEFAULT_ARMIPS,
    game: str = "firered",
) -> Path:
    """Apply Chinese font patch to a ROM.

    For FireRed/LeafGreen:
        1. Copy ROM to pokeFRLG/baserom_FR.gba
        2. Run armips on main_FR.asm (hardcoded filenames)
        3. Copy chsfontrom_FR.gba to output_path

    For Emerald:
        1. Copy ROM to pokeE/baserom_E.gba
        2. Run armips on main_E.asm with -strequ params
        3. Copy baserom_E_chs.gba to output_path
    """
    cfg = _GAME_CONFIG.get(game)
    if cfg is None:
        raise ValueError(f"Unsupported game for font patch: {game}")

    font_patch_dir = _PATCH_ROOT / cfg["subdir"]
    baserom = font_patch_dir / cfg["baserom"]
    patched = font_patch_dir / cfg["output"]
    asm_file = font_patch_dir / cfg["asm"]

    # Copy ROM as baserom
    shutil.copy2(rom_path, baserom)

    # Build armips command
    if cfg["use_strequ"]:
        cmd = [
            str(armips_path),
            str(asm_file),
            "-strequ", "Origin_Rom", str(baserom),
            "-strequ", "Chinese_Patched_Rom", str(patched),
        ]
    else:
        cmd = [str(armips_path), str(asm_file)]

    result = subprocess.run(
        cmd,
        cwd=str(font_patch_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"armips failed:\n{result.stderr}\n{result.stdout}")

    if not patched.exists():
        raise RuntimeError(f"Font patch output not found: {patched}")

    # Copy patched ROM to output
    shutil.copy2(patched, output_path)

    # Clean up
    baserom.unlink(missing_ok=True)
    patched.unlink(missing_ok=True)

    return output_path
