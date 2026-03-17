"""Main text extraction orchestrator.

This module provides the high-level extract_texts() function that
orchestrates all extraction phases, replicating TextExtractor.ExtractAll()
from TextExtractor.cs lines 19-42.
"""

import json
from pathlib import Path
from typing import Dict, List

from .gba_rom import GbaRom
from .script_extractor import ScriptExtractor
from .table_extractor import TableExtractor


def extract_texts(rom_path: Path, output_path: Path) -> Path:
    """Extract all texts from a GBA Pokemon ROM.

    This is the pure Python replacement for MeowthBridge's extract command.
    Replicates TextExtractor.ExtractAll() from TextExtractor.cs.

    Args:
        rom_path: Path to input ROM file
        output_path: Path to output JSON file

    Returns:
        Path to output JSON file

    Raises:
        ValueError: If ROM is not supported
        FileNotFoundError: If ROM file doesn't exist
    """
    # Load ROM
    rom = GbaRom(rom_path)
    print(f"Loaded ROM: {rom.game_name} ({rom.game_code})", flush=True)

    # Track extracted addresses to avoid duplicates
    extracted_addresses = set()
    id_counter = 0
    all_entries = []

    # Phase 1: Extract table texts (100% accurate, HMA-identified tables)
    print("Phase 1: Extracting table texts...", flush=True)
    table_extractor = TableExtractor(rom)
    table_entries, id_counter = table_extractor.extract_all(extracted_addresses, id_counter)
    all_entries.extend(table_entries)
    print(f"  Table texts: {len(table_entries)} entries", flush=True)

    # Phase 2: Scan loadpointer instructions, build safe pointer source map
    print("Phase 2: Scanning loadpointer instructions...", flush=True)
    script_extractor = ScriptExtractor(rom)
    loadpointer_map = script_extractor.scan_loadpointer_sources()
    print(f"  Found {len(loadpointer_map)} text addresses with loadpointer references", flush=True)

    # Phase 3: Extract loadpointer-referenced texts (script-referenced, very safe)
    print("Phase 3: Extracting loadpointer texts...", flush=True)
    before_lp = len(all_entries)
    script_entries, id_counter = script_extractor.extract_loadpointer_texts(
        loadpointer_map, extracted_addresses, id_counter
    )
    all_entries.extend(script_entries)
    print(f"  Loadpointer texts: {len(all_entries) - before_lp} entries", flush=True)

    # Write output JSON
    output_data = {"entries": all_entries}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\nTotal extracted: {len(all_entries)} entries", flush=True)
    print(f"Output written to: {output_path}", flush=True)

    return output_path
