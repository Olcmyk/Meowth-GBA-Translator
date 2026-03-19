#!/usr/bin/env python3
"""
Custom script to extract text from Emerald ROM, replace letters before spaces with '2',
and write back to outputs/
"""
import json
import re
from pathlib import Path
from meowth.core import TranslationEngine, TranslationConfig, TranslationCallbacks

class SimpleCallbacks(TranslationCallbacks):
    """Simple callback implementation for printing progress."""
    def on_log(self, level: str, message: str):
        print(message)

def modify_text(text: str) -> str:
    """Replace all letters before spaces with the number '2'."""
    # Pattern: any letter followed by a space
    # Replace the letter (not the space) with '2'
    return re.sub(r'[a-zA-Z](?= )', '2', text)

def main():
    rom_path = Path("testgba/1986 - Pokemon Emerald (U)(TrashMan).gba")
    output_dir = Path("outputs")
    work_dir = Path("work")

    # Create directories
    output_dir.mkdir(exist_ok=True)
    work_dir.mkdir(exist_ok=True)

    print(f"Processing ROM: {rom_path}")

    # Step 1: Extract text
    print("\n[1/3] Extracting text from ROM...")
    extracted_json = work_dir / "emerald_extracted.json"
    TranslationEngine.extract_texts(rom_path, extracted_json)
    print(f"Extracted to: {extracted_json}")

    # Step 2: Modify text
    print("\n[2/3] Modifying text (replacing letters before spaces with '2')...")
    with open(extracted_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Track modifications
    modified_count = 0
    total_texts = 0

    # The JSON has an "entries" array with objects containing "original" field
    # We need to add a "translated" field (not "translation") with the modified text
    if "entries" in data:
        for entry in data["entries"]:
            if "original" in entry and isinstance(entry["original"], str):
                total_texts += 1
                original = entry["original"]
                # Remove quotes if present
                text = original.strip('"')
                modified = modify_text(text)

                # Add the "translated" field with the modified text
                if text != modified:
                    entry["translated"] = f'"{modified}"' if original.startswith('"') else modified
                    modified_count += 1
                else:
                    # Even if not modified, add translated field for consistency
                    entry["translated"] = original

    print(f"Modified {modified_count} out of {total_texts} text entries")

    # Save modified JSON
    modified_json = work_dir / "emerald_modified.json"
    with open(modified_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved modified text to: {modified_json}")

    # Step 3: Build ROM with modified text
    print("\n[3/3] Building ROM with modified text...")
    output_rom = output_dir / "1986 - Pokemon Emerald (U)(TrashMan)_modified.gba"

    # Create engine for building
    config = TranslationConfig(source_lang="en", target_lang="en")
    engine = TranslationEngine(config, SimpleCallbacks())
    engine.build_rom(rom_path, modified_json, output_rom)

    print(f"\n✓ Success! Modified ROM saved to: {output_rom}")

    # Show some examples
    print("\n--- Example modifications ---")
    example_count = 0
    if "entries" in data:
        for entry in data["entries"]:
            if "original" in entry and isinstance(entry["original"], str):
                text = entry["original"]
                # Show entries that contain spaces and were likely modified
                if ' ' in text and any(c.isalpha() for c in text):
                    print(f"{entry.get('id', 'unknown')}: {text[:80]}")
                    example_count += 1
                    if example_count >= 5:
                        break

if __name__ == "__main__":
    main()
