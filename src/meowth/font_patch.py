"""Apply Pokemon_GBA_Font_Patch via armips."""

import shutil
import subprocess
from pathlib import Path

FONT_PATCH_DIR = Path(__file__).parent.parent.parent / "Pokemon_GBA_Font_Patch" / "pokeFRLG"
DEFAULT_ARMIPS = Path(__file__).parent.parent.parent / "tools" / "armips"


def apply_font_patch(
    rom_path: Path,
    output_path: Path,
    armips_path: Path = DEFAULT_ARMIPS,
    font_patch_dir: Path = FONT_PATCH_DIR,
) -> Path:
    """Apply Chinese font patch to a ROM.

    1. Copy ROM to font_patch_dir/baserom_FR.gba
    2. Run armips on main_FR.asm
    3. Copy output to output_path
    """
    baserom = font_patch_dir / "baserom_FR.gba"
    patched = font_patch_dir / "chsfontrom_FR.gba"

    # Copy ROM as baserom
    shutil.copy2(rom_path, baserom)

    # Run armips from the font patch directory (it uses relative paths)
    asm_file = font_patch_dir / "main_FR.asm"
    result = subprocess.run(
        [str(armips_path), str(asm_file)],
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
