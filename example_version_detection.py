#!/usr/bin/env python3
"""Example: Using version detection and decomp ROM checking."""

from pathlib import Path
from src.meowth.core import TranslationConfig, TranslationEngine, TranslationCallbacks
from src.meowth.core.engine import detect_game, is_decomp_rom
from src.meowth.languages import is_cjk_language


class SimpleCallbacks(TranslationCallbacks):
    """Simple callback implementation for examples."""

    def on_log(self, level: str, message: str):
        print(f"[{level.upper()}] {message}")


def check_rom_compatibility(rom_path: Path, target_lang: str) -> bool:
    """Check if ROM is compatible with target language.

    Args:
        rom_path: Path to ROM file
        target_lang: Target language code (e.g., "zh-Hans", "es")

    Returns:
        True if compatible, False otherwise
    """
    print(f"\n=== Checking ROM Compatibility ===")
    print(f"ROM: {rom_path.name}")
    print(f"Target language: {target_lang}\n")

    # Step 1: Detect game version
    game = detect_game(rom_path)
    print(f"✓ Detected game: {game}")

    if game == "unknown":
        print("✗ Unknown game version!")
        return False

    # Step 2: Check if target language requires font injection
    requires_font = is_cjk_language(target_lang)
    print(f"✓ Requires font injection: {requires_font}")

    # Step 3: Check for decomp ROM (only if font injection needed)
    if requires_font:
        is_decomp = is_decomp_rom(rom_path)
        print(f"✓ Is decomp ROM: {is_decomp}")

        if is_decomp:
            print("\n✗ INCOMPATIBLE: Decomp ROM cannot be translated to CJK languages")
            print("  Reason: Font injection not supported for decomp ROMs")
            print("  Solution: Use binary ROM or translate to Latin languages")
            return False

    print("\n✓ COMPATIBLE: ROM can be translated to target language")
    return True


def translate_with_safety_check(rom_path: Path, target_lang: str = "zh-Hans"):
    """Translate ROM with safety checks.

    Args:
        rom_path: Path to ROM file
        target_lang: Target language code
    """
    # Check compatibility first
    if not check_rom_compatibility(rom_path, target_lang):
        print("\nTranslation aborted due to compatibility issues.")
        return

    # Proceed with translation
    print("\n=== Starting Translation ===\n")

    config = TranslationConfig(
        source_lang="en",
        target_lang=target_lang,
        rom_path=rom_path,
        output_dir=Path("outputs"),
        work_dir=Path("work"),
    )

    engine = TranslationEngine(config, SimpleCallbacks())

    try:
        output = engine.run_full()
        print(f"\n✓ Translation completed: {output}")
    except Exception as e:
        print(f"\n✗ Translation failed: {e}")


def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python example_version_detection.py <rom_path> [target_lang]")
        print("\nExamples:")
        print("  python example_version_detection.py pokemon_firered.gba zh-Hans")
        print("  python example_version_detection.py pokemon_emerald.gba es")
        print("  python example_version_detection.py pokeemerald.gba zh-Hans  # Will fail")
        return

    rom_path = Path(sys.argv[1])
    target_lang = sys.argv[2] if len(sys.argv) > 2 else "zh-Hans"

    if not rom_path.exists():
        print(f"Error: ROM file not found: {rom_path}")
        return

    # Example 1: Just check compatibility
    print("=" * 60)
    print("Example 1: Check ROM Compatibility")
    print("=" * 60)
    check_rom_compatibility(rom_path, target_lang)

    # Example 2: Translate with safety check (commented out to avoid actual translation)
    # print("\n" + "=" * 60)
    # print("Example 2: Translate with Safety Check")
    # print("=" * 60)
    # translate_with_safety_check(rom_path, target_lang)


if __name__ == "__main__":
    main()
