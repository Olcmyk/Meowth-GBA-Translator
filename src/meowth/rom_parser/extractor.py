"""Main text extraction orchestrator.

This module provides the high-level :func:`extract_texts` function and a
small amount of game-specific supplementation for texts that are known to be
missed by pure table/loadpointer extraction.
"""

import json
from pathlib import Path
from typing import Dict, List

from .gba_rom import GbaRom
from .pcs_decoder import PcsDecoder
from .script_extractor import ScriptExtractor
from .table_extractor import TableExtractor

_FIRERED_MISSING_PC_TEXTS = [
    (0x4178BE, [0x10DA18], "pointers"),
    (0x417B9F, [0x09D248], "pointers"),
    (0x417BAC, [0x09D1E0], "pointers"),
    (0x417BB6, [0x09D11C, 0x09D250], "pointers"),
    (0x417BD3, [0x09D128, 0x09D1D4], "pointers"),
    (0x41856C, [0x3CDA20], "menu_pcoptions"),
    (0x41857D, [0x3CDA28], "menu_pcoptions"),
    (0x41858D, [0x3CDA30], "menu_pcoptions"),
    (0x41859A, [0x3CDA38], "menu_pcoptions"),
    (0x4185A5, [0x3CDA40], "menu_pcoptions"),
    (0x4185AD, [0x3CDA24], "pointers"),
    (0x418681, [0x08C594], "pointers"),
]


def _extract_known_missing_firered_pc_texts(
    rom: GbaRom,
    extracted_addresses: set[int],
    id_counter: int,
) -> tuple[list[dict], int]:
    """Supplement FireRed with PC/menu texts that the safe scanners miss."""
    if not rom.game_code.startswith("BPRE"):
        return [], id_counter

    decoder = PcsDecoder(rom.data)
    entries: list[dict] = []

    for text_addr, ptr_sources, category in _FIRERED_MISSING_PC_TEXTS:
        if text_addr in extracted_addresses:
            continue

        text_length = decoder.validate_pcs_text(text_addr)
        if text_length < 2:
            continue

        text = decoder.decode_pcs_text(text_addr, text_length)
        if not text or text == '""':
            continue

        extracted_addresses.add(text_addr)
        entry = {
            "id": f"ptr_{id_counter:05d}",
            "category": category,
            "address": f"0x{text_addr:X}",
            "pointer_sources": [f"0x{p:X}" for p in ptr_sources],
            "original": text,
            "byte_length": text_length,
            "is_pointer_based": True,
            "table_name": None,
            "table_index": None,
        }
        entries.append(entry)
        id_counter += 1

    return entries, id_counter


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

    # Phase 4: supplement known safe misses in FireRed PC/menu text
    print("Phase 4: Supplementing known missed PC/menu texts...", flush=True)
    missing_entries, id_counter = _extract_known_missing_firered_pc_texts(
        rom, extracted_addresses, id_counter
    )
    all_entries.extend(missing_entries)
    print(f"  Supplemental texts: {len(missing_entries)} entries", flush=True)

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
