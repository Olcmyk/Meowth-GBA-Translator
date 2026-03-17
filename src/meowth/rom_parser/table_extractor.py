"""Table text extraction from GBA ROMs.

This module extracts text from hardcoded tables (Phase 1 of extraction).
Replicates ExtractTableTexts() from TextExtractor.cs lines 44-109.
"""

from typing import Dict, List, Set

from .gba_rom import GbaRom
from .pcs_decoder import PcsDecoder
from .table_definitions import TableDefinition, get_tables_for_game


class TableExtractor:
    """Extracts text from hardcoded ROM tables.

    Replicates Phase 1 extraction logic from TextExtractor.cs.
    """

    def __init__(self, rom: GbaRom):
        """Initialize table extractor.

        Args:
            rom: GBA ROM to extract from
        """
        self.rom = rom
        self.decoder = PcsDecoder(rom.data)
        self.tables = get_tables_for_game(rom.game_code)

    def extract_all(self, extracted_addresses: Set[int], id_counter: int) -> tuple[List[Dict], int]:
        """Extract all table texts.

        Args:
            extracted_addresses: Set to track extracted addresses (modified in-place)
            id_counter: Starting ID counter for entries

        Returns:
            Tuple of (entries list, updated id_counter)
        """
        entries = []

        for table_def in self.tables:
            table_entries = self._extract_table(table_def, extracted_addresses, id_counter)
            entries.extend(table_entries)
            id_counter += len(table_entries)

        return entries, id_counter

    def _find_text_length(self, address: int, max_length: int = 2000) -> int:
        """Find PCS text length by scanning for 0xFF terminator.

        For table text, we don't validate letter count - HMA already knows
        these are valid text locations. We just find the terminator.

        Args:
            address: ROM offset to scan
            max_length: Maximum bytes to scan

        Returns:
            Text length including terminator, or 0 if not found
        """
        if address < 0 or address >= len(self.rom.data):
            return 0

        for i in range(max_length):
            if address + i >= len(self.rom.data):
                return 0
            if self.rom.data[address + i] == 0xFF:
                return i + 1

        return 0

    def _extract_table(
        self,
        table_def: TableDefinition,
        extracted_addresses: Set[int],
        id_counter: int
    ) -> List[Dict]:
        """Extract text from a single table.

        Replicates ExtractTableTexts() logic from TextExtractor.cs lines 78-108.

        Args:
            table_def: Table definition
            extracted_addresses: Set to track extracted addresses
            id_counter: Starting ID for this table's entries

        Returns:
            List of entry dictionaries
        """
        entries = []

        # Check if this is a variable-length sequential table
        # These tables have strings packed sequentially, not at fixed offsets
        if table_def.is_sequential:
            # Sequential variable-length strings (e.g., nature names)
            current_addr = table_def.address
            for i in range(table_def.count):
                text_address = current_addr

                # Find text length
                text_length = self._find_text_length(text_address)
                if text_length < 1:
                    break  # Can't continue if we can't find terminator

                # Decode text
                text = self.decoder.decode_pcs_text(text_address, text_length)

                # Skip empty text
                if not text or text == '""':
                    current_addr += text_length
                    continue

                # Mark address as extracted
                extracted_addresses.add(text_address)

                # Create entry
                entry = {
                    "id": f"tbl_{table_def.category}_{id_counter:05d}",
                    "category": table_def.category,
                    "address": f"0x{text_address:X}",
                    "pointer_sources": [],
                    "original": text,
                    "byte_length": text_length,  # For sequential tables, use actual length
                    "is_pointer_based": table_def.is_pointer_based,
                    "table_name": table_def.name,
                    "table_index": i,
                }
                entries.append(entry)
                id_counter += 1

                # Move to next string
                current_addr += text_length
        else:
            # Fixed-size entries (e.g., pokemon names, item stats)
            for i in range(table_def.count):
                # Calculate entry start address
                element_start = table_def.address + i * table_def.entry_size

                if table_def.is_pointer_based:
                    # Pointer-based table: read pointer, follow it to text
                    text_address = self.rom.read_pointer(element_start)
                    if text_address < 0:
                        continue

                    # Find text length (scan for 0xFF terminator)
                    text_length = self._find_text_length(text_address)
                    if text_length < 1:
                        continue

                    # Decode text
                    text = self.decoder.decode_pcs_text(text_address, text_length)
                else:
                    # Inline text table: text is directly at element_start
                    text_address = element_start

                    # For inline tables, use the entry_size as max length
                    # Find actual text length by scanning for terminator
                    text_length = self._find_text_length(text_address, max_length=table_def.entry_size)
                    if text_length < 1:
                        continue

                    # Decode text
                    text = self.decoder.decode_pcs_text(text_address, text_length)

                # Skip empty text
                if not text or text == '""':
                    continue

                # Mark address as extracted
                extracted_addresses.add(text_address)

                # Create entry (matching C# TextEntry structure)
                # For byte_length: use text_length if specified (for complex tables like items.stats),
                # otherwise use entry_size for inline tables or actual length for pointer-based
                reported_length = table_def.text_length if table_def.text_length else (
                    table_def.entry_size if not table_def.is_pointer_based else text_length
                )
                entry = {
                    "id": f"tbl_{table_def.category}_{id_counter:05d}",
                    "category": table_def.category,
                    "address": f"0x{text_address:X}",
                    "pointer_sources": [],
                    "original": text,
                    "byte_length": reported_length,
                    "is_pointer_based": table_def.is_pointer_based,
                    "table_name": table_def.name,
                    "table_index": i,
                }
                entries.append(entry)
                id_counter += 1

        return entries
