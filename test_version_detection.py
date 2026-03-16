#!/usr/bin/env python3
"""Test script for version detection and decomp ROM detection."""

from pathlib import Path
from src.meowth.core.engine import detect_game, is_decomp_rom, _GAME_CODES

def test_version_detection():
    """Test game version detection."""
    print("=== Testing Version Detection ===\n")

    print("Supported game codes:")
    for code, name in _GAME_CODES.items():
        print(f"  {code} -> {name}")

    print("\nTo test with a real ROM:")
    print("  python test_version_detection.py <rom_path>")

def test_decomp_detection(rom_path: Path):
    """Test decomp ROM detection."""
    print(f"\n=== Testing ROM: {rom_path.name} ===\n")

    # Detect game version
    game = detect_game(rom_path)
    print(f"Detected game: {game}")

    # Check if decomp
    is_decomp = is_decomp_rom(rom_path)
    print(f"Is decomp ROM: {is_decomp}")

    if is_decomp:
        print("\n⚠️  This is a decomp ROM!")
        print("Cannot translate to Chinese (requires font injection)")
    else:
        print("\n✅ This is a binary ROM")
        print("Can be translated to any language")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        rom_path = Path(sys.argv[1])
        if rom_path.exists():
            test_decomp_detection(rom_path)
        else:
            print(f"Error: ROM file not found: {rom_path}")
    else:
        test_version_detection()
