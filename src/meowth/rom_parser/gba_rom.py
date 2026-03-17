"""GBA ROM loading and structure parsing.

This module replicates the ROM loading logic from RomLoader.cs,
providing byte-level access to ROM data and game identification.
"""

from pathlib import Path
from typing import BinaryIO


# Game code mapping (from offset 0xAC)
GAME_CODES = {
    "BPRE": "firered",
    "BPGE": "leafgreen",
    "BPEE": "emerald",
    "AXVE": "ruby",
    "AXPE": "sapphire",
}


class GbaRom:
    """Represents a GBA ROM file with byte-level access.

    Replicates HardcodeTablesModel's ROM loading behavior from HMA.
    """

    def __init__(self, rom_path: Path):
        """Load a GBA ROM from file.

        Args:
            rom_path: Path to the .gba ROM file
        """
        self.path = rom_path
        self.data = bytearray(rom_path.read_bytes())
        self.game_code = self._read_game_code()
        self.game_name = GAME_CODES.get(self.game_code[:4], "unknown")

    def _read_game_code(self) -> str:
        """Extract game code from ROM header.

        Game code is at offset 0xAC (4 bytes) + version at 0xBC (1 byte).
        Example: "BPRE0" for FireRed version 0.

        Returns:
            Game code string (e.g., "BPRE0")
        """
        # Read 4-byte game code at 0xAC
        code = self.data[0xAC:0xB0].decode("ascii", errors="replace")
        # Append version byte at 0xBC
        version = str(self.data[0xBC])
        return code + version

    def __getitem__(self, index: int | slice) -> int | bytearray:
        """Access ROM bytes by index or slice.

        Args:
            index: Byte offset or slice

        Returns:
            Single byte (int) or byte array
        """
        result = self.data[index]
        if isinstance(index, slice):
            return bytearray(result)
        return result

    def __len__(self) -> int:
        """Get ROM size in bytes."""
        return len(self.data)

    def read_pointer(self, offset: int) -> int:
        """Read a 4-byte GBA pointer and convert to ROM offset.

        GBA pointers are stored in little-endian format with 0x08000000 base.
        This method reads the pointer and subtracts the base to get ROM offset.

        Args:
            offset: ROM offset where pointer is stored

        Returns:
            ROM offset (pointer - 0x08000000), or -1 if invalid
        """
        if offset < 0 or offset + 4 > len(self.data):
            return -1

        # Read 4 bytes in little-endian
        ptr_bytes = self.data[offset:offset + 4]
        pointer = int.from_bytes(ptr_bytes, byteorder='little')

        # GBA ROM pointers have 0x08000000 base
        if pointer < 0x08000000:
            return -1

        rom_offset = pointer - 0x08000000

        # Validate offset is within ROM
        if rom_offset < 0 or rom_offset >= len(self.data):
            return -1

        return rom_offset
