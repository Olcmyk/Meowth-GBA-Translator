"""Script text extraction via loadpointer instruction scanning.

This module extracts text referenced by loadpointer (0x0F) instructions
(Phase 2 & 3 of extraction). Replicates ScanLoadpointerSources() and
ExtractLoadpointerTexts() from TextExtractor.cs lines 141-215.
"""

from typing import Dict, List, Set

from .gba_rom import GbaRom
from .pcs_decoder import PcsDecoder


class ScriptExtractor:
    """Extracts script text via loadpointer instruction scanning.

    Replicates Phase 2 & 3 extraction logic from TextExtractor.cs.
    """

    def __init__(self, rom: GbaRom):
        """Initialize script extractor.

        Args:
            rom: GBA ROM to extract from
        """
        self.rom = rom
        self.decoder = PcsDecoder(rom.data)

    def scan_loadpointer_sources(self) -> Dict[int, Set[int]]:
        """Scan ROM for loadpointer (0x0F) instructions.

        Replicates ScanLoadpointerSources() from TextExtractor.cs lines 146-176.

        This is the only safe way to find pointer sources: trust explicit
        loadpointer instructions in scripts, not HMA's SearchForPointers
        (which does 4-byte aligned scanning and can misidentify jump tables).

        Returns:
            Dictionary mapping text_address -> set of pointer_source_addresses
        """
        loadpointer_map: Dict[int, Set[int]] = {}

        # Scan script section starting at 0x0A0000
        i = 0x0A0000
        while i < len(self.rom.data) - 6:
            # Check for loadpointer opcode
            if self.rom[i] != 0x0F:
                i += 1
                continue

            # GBA Pokemon script engine only has 4 banks (0-3).
            # Any other value means this 0x0F byte is data, not a loadpointer.
            bank = self.rom[i + 1]
            if bank > 3:
                i += 1
                continue

            # Read pointer at offset i+2
            ptr_offset = i + 2
            if ptr_offset + 4 > len(self.rom.data):
                i += 1
                continue

            pointer = self.rom.read_pointer(ptr_offset)
            if pointer < 0 or pointer >= len(self.rom.data):
                i += 1
                continue

            # Validate that pointer points to valid PCS text
            text_length = self.decoder.validate_pcs_text(pointer)
            if text_length < 2:
                i += 1
                continue

            # Valid loadpointer instruction found
            if pointer not in loadpointer_map:
                loadpointer_map[pointer] = set()
            loadpointer_map[pointer].add(ptr_offset)

            # Skip past this instruction: opcode(1) + bank(1) + pointer(4) = 6 bytes
            # But loop will i++, so skip 5 more
            i += 5

        return loadpointer_map

    def extract_loadpointer_texts(
        self,
        loadpointer_map: Dict[int, Set[int]],
        extracted_addresses: Set[int],
        id_counter: int
    ) -> tuple[List[Dict], int]:
        """Extract texts referenced by loadpointer instructions.

        Replicates ExtractLoadpointerTexts() from TextExtractor.cs lines 182-215.

        Args:
            loadpointer_map: Map from text_address to pointer_source_addresses
            extracted_addresses: Set of already-extracted addresses (modified in-place)
            id_counter: Starting ID counter

        Returns:
            Tuple of (entries list, updated id_counter)
        """
        entries = []

        for text_addr, ptr_sources in loadpointer_map.items():
            # Skip if already extracted in Phase 1 (table text)
            if text_addr in extracted_addresses:
                continue

            # Validate PCS text
            text_length = self.decoder.validate_pcs_text(text_addr)
            if text_length < 2:
                continue

            # Decode text
            text = self.decoder.decode_pcs_text(text_addr, text_length)
            if not text or text == '""':
                continue

            # Clean text (strip quotes for length check)
            clean_text = text.strip('"')
            if len(clean_text) < 1:
                continue

            # Mark as extracted
            extracted_addresses.add(text_addr)

            # Create entry (matching C# TextEntry structure)
            entry = {
                "id": f"scr_{id_counter:05d}",
                "category": "scripts",
                "address": f"0x{text_addr:X}",
                "pointer_sources": [f"0x{p:X}" for p in sorted(ptr_sources)],
                "original": text,
                "byte_length": text_length,
                "is_pointer_based": True,
                "table_name": None,
                "table_index": None,
            }
            entries.append(entry)
            id_counter += 1

        return entries, id_counter
