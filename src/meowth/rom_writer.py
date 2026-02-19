"""ROM expansion, text injection, and pointer updates."""

from pathlib import Path

from .charmap import Charmap

# Font Patch injects data at GBA address 0x09FD3000 = ROM offset 0x01FD3000
# We must not write past this boundary
FONT_PATCH_BOUNDARY = 0x01FD3000
ROM_32MB = 0x02000000
GBA_ROM_BASE = 0x08000000
TERMINATOR = 0xFF


class RomWriter:
    def __init__(self, charmap: Charmap):
        self.charmap = charmap
        self.free_ptr = 0  # next free space pointer

    def load_rom(self, path: Path) -> bytearray:
        return bytearray(path.read_bytes())

    def expand_rom(self, rom: bytearray, target_size: int = ROM_32MB) -> bytearray:
        """Expand ROM to target size, filling with 0xFF."""
        if len(rom) < target_size:
            rom.extend(b"\xFF" * (target_size - len(rom)))
        return rom

    def encode_text(self, text: str) -> bytearray:
        """Encode translated text to ROM bytes.

        Handles mixed content: control codes keep PCS bytes,
        regular characters go through charmap.
        """
        result = bytearray()
        i = 0
        while i < len(text):
            # Check for HMA-style control codes
            if text[i] == "\\" and i + 1 < len(text):
                code_bytes = self._encode_control_code(text, i)
                if code_bytes is not None:
                    result.extend(code_bytes[0])
                    i += code_bytes[1]
                    continue

            # Regular character through charmap
            encoded = self.charmap.encode_char(text[i])
            if encoded is None:
                # Skip unsupported characters
                i += 1
                continue
            result.extend(encoded)
            i += 1

        return result

    def _encode_control_code(self, text: str, pos: int) -> tuple[bytes, int] | None:
        """Try to encode a control code starting at pos. Returns (bytes, chars_consumed) or None."""
        # Common PCS control codes
        codes = {
            "\\n": b"\xFE",    # newline
            "\\l": b"\xFA",    # line scroll
            "\\p": b"\xFB",    # paragraph
            "\\e": b"\xFC",    # escape (followed by command byte)
        }
        remaining = text[pos:]
        for code_str, code_bytes in codes.items():
            if remaining.startswith(code_str):
                return code_bytes, len(code_str)

        # \v followed by 2 hex chars (variable)
        if remaining.startswith("\\v") and len(remaining) >= 4:
            try:
                val = int(remaining[2:4], 16)
                return bytes([0xFD, val]), 4
            except ValueError:
                pass

        # [player] and [rival] - these are multi-byte sequences
        if remaining.startswith("[player]"):
            return b"\xFD\x01", 8
        if remaining.startswith("[rival]"):
            return b"\xFD\x06", 7

        return None

    def inject_texts(
        self,
        rom: bytearray,
        entries: list[dict],
        start_offset: int = 0x01000000,
    ) -> tuple[bytearray, dict]:
        """Inject translated texts into ROM.

        Args:
            rom: ROM bytearray (should be expanded to 32MB and font-patched)
            entries: list of dicts with 'address', 'pointer_addresses', 'translated',
                     'max_bytes', 'is_pointer' keys
            start_offset: where to start writing relocated text

        Returns:
            (modified_rom, stats_dict)
        """
        self.free_ptr = start_offset
        stats = {"in_place": 0, "relocated": 0, "skipped": 0}

        for entry in entries:
            translated = entry.get("translated", "")
            original = entry.get("original", "")
            if not translated or translated == original:
                stats["skipped"] += 1
                continue

            encoded = self.encode_text(translated)
            encoded.append(TERMINATOR)

            address = int(entry["address"], 16)
            max_bytes = entry.get("max_bytes", 0)
            is_pointer = entry.get("is_pointer", False)
            ptr_addrs = [int(p, 16) for p in entry.get("pointer_addresses", [])]

            if not is_pointer and max_bytes > 0 and len(encoded) <= max_bytes:
                # Write in place, pad with 0xFF
                rom[address : address + len(encoded)] = encoded
                remaining = max_bytes - len(encoded)
                if remaining > 0:
                    rom[address + len(encoded) : address + max_bytes] = (
                        b"\xFF" * remaining
                    )
                stats["in_place"] += 1
            elif ptr_addrs:
                # Relocate to free space
                if self.free_ptr + len(encoded) >= FONT_PATCH_BOUNDARY:
                    stats["skipped"] += 1
                    continue

                rom[self.free_ptr : self.free_ptr + len(encoded)] = encoded
                # Update all pointers
                for ptr_addr in ptr_addrs:
                    self._write_pointer(rom, ptr_addr, self.free_ptr)
                self.free_ptr += len(encoded)
                # Align to 4 bytes
                self.free_ptr = (self.free_ptr + 3) & ~3
                stats["relocated"] += 1
            else:
                stats["skipped"] += 1

        return rom, stats

    def _write_pointer(self, rom: bytearray, ptr_addr: int, target: int):
        """Write a GBA pointer (little-endian + 0x08000000 base)."""
        value = target + GBA_ROM_BASE
        rom[ptr_addr : ptr_addr + 4] = value.to_bytes(4, "little")

    def save_rom(self, rom: bytearray, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(rom)
