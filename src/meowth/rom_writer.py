"""ROM expansion, text injection, and pointer updates."""

from pathlib import Path

from .charmap import Charmap
from .pcs_codes import (
    BACKSLASH_CODES,
    BRACKET_MACROS,
    CONTROL_CODE_PREFIX,
    ESCAPE_PREFIX,
    BUTTON_PREFIX,
    F7_PREFIX,
    F9_PREFIX,
    F6_BYTE,
    NEWLINE,
    PARAGRAPH,
    TERMINATOR,
    fc_arg_count,
)

# Font Patch injects data at GBA address 0x09FD3000 = ROM offset 0x01FD3000
# We must not write past this boundary
FONT_PATCH_BOUNDARY = 0x01FD3000
ROM_32MB = 0x02000000
GBA_ROM_BASE = 0x08000000


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

        Handles mixed content: HMA control codes → PCS bytes,
        regular characters → charmap.
        HMA exports: \n\n = paragraph wait (0xFB), single \n = newline (0xFE).
        """
        result = bytearray()
        i = 0
        while i < len(text):
            # Double newline = paragraph wait (PCS 0xFB)
            if text[i] == "\n" and i + 1 < len(text) and text[i + 1] == "\n":
                result.append(PARAGRAPH)
                i += 2
                continue

            # Single newline = PCS newline (0xFE)
            if text[i] == "\n":
                result.append(NEWLINE)
                i += 1
                continue

            # Check for [...] macro sequences
            if text[i] == "[":
                macro_result = self._encode_macro(text, i)
                if macro_result is not None:
                    result.extend(macro_result[0])
                    i += macro_result[1]
                    continue

            # Check for HMA backslash control codes
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
        """Encode an HMA backslash control code at pos."""
        remaining = text[pos:]

        # \CC followed by hex bytes — 0xFC + command byte + variable args
        if remaining.startswith("\\CC"):
            return self._encode_cc_code(remaining)

        # \btn followed by 2 hex chars — 0xF8 + button ID
        if remaining.startswith("\\btn") and len(remaining) >= 6:
            try:
                val = int(remaining[4:6], 16)
                return bytes([BUTTON_PREFIX, val]), 6
            except ValueError:
                pass

        # \9 followed by 2 hex chars — 0xF9 + byte
        if remaining.startswith("\\9") and len(remaining) >= 4:
            try:
                val = int(remaining[2:4], 16)
                return bytes([F9_PREFIX, val]), 4
            except ValueError:
                pass

        # \? followed by 2 hex chars — 0xF7 + byte
        if remaining.startswith("\\?") and len(remaining) >= 4:
            try:
                val = int(remaining[2:4], 16)
                return bytes([F7_PREFIX, val]), 4
            except ValueError:
                pass

        # \F6 — raw single byte
        if remaining.startswith("\\F6"):
            return bytes([F6_BYTE]), 3

        # Simple backslash codes from shared definitions
        for code_str, code_bytes in BACKSLASH_CODES:
            if remaining.startswith(code_str):
                return code_bytes, len(code_str)

        # \\ (double backslash) = 0xFD escape, next byte is raw
        if remaining.startswith("\\\\") and len(remaining) >= 4:
            try:
                val = int(remaining[2:4], 16)
                return bytes([ESCAPE_PREFIX, val]), 4
            except ValueError:
                pass

        return None

    def _encode_cc_code(self, remaining: str) -> tuple[bytes, int] | None:
        """Encode \\CC control code with variable-length hex arguments."""
        hex_start = 3  # skip \CC
        hex_chars = ""
        j = hex_start
        while j < len(remaining) and remaining[j] in "0123456789ABCDEFabcdef":
            hex_chars += remaining[j]
            j += 1

        if len(hex_chars) < 2:
            return None

        result = bytearray([CONTROL_CODE_PREFIX])
        byte_count = len(hex_chars) // 2
        for k in range(byte_count):
            val = int(hex_chars[k * 2 : k * 2 + 2], 16)
            result.append(val)

        consumed = 3 + byte_count * 2
        return bytes(result), consumed

    def _encode_macro(self, text: str, pos: int) -> tuple[bytes, int] | None:
        """Encode [...] macro sequences using shared definitions."""
        remaining = text[pos:]
        for macro_str, macro_bytes in BRACKET_MACROS.items():
            if remaining.startswith(macro_str):
                return macro_bytes, len(macro_str)
        return None

    @staticmethod
    def _is_safe_pointer(rom: bytearray, ptr_addr: int, text_addr: int) -> bool:
        """Check if a pointer address is safe to update.

        A pointer is safe if:
        1. It's within ROM bounds
        2. It currently points to the expected text address
        3. It's not in the first 0x8000 bytes (ROM header + early code)

        FireRed ROM layout:
        - 0x000000-0x008000: Header, interrupt vectors, critical early code
        - 0x008000-0x100000: Game code (but some data tables exist here too)
        - 0x100000+: Scripts, text, and data

        We use a conservative 0x8000 threshold to avoid corrupting critical
        boot code while still allowing script pointer updates.
        """
        # Basic bounds check
        if ptr_addr + 4 > len(rom):
            return False

        # Skip first 32KB - ROM header and critical boot code
        if ptr_addr < 0x8000:
            return False

        # Read current pointer value and validate it points to expected address
        current_val = int.from_bytes(rom[ptr_addr : ptr_addr + 4], "little")
        expected_val = text_addr + GBA_ROM_BASE

        return current_val == expected_val

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
        stats = {
            "in_place": 0,
            "relocated": 0,
            "skipped": 0,
            "skipped_partial_ptrs": 0,  # Skipped because not all pointers were safe
            "unsafe_ptrs": 0,
        }

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
            all_ptrs = [int(p, 16) for p in entry.get("pointer_addresses", [])]

            # Filter to only safe pointer addresses
            safe_ptrs = [p for p in all_ptrs if self._is_safe_pointer(rom, p, address)]
            unsafe_count = len(all_ptrs) - len(safe_ptrs)
            stats["unsafe_ptrs"] += unsafe_count

            # encoded already includes terminator (added above)
            if not is_pointer and max_bytes > 0 and len(encoded) <= max_bytes:
                # Write in place, pad with 0xFF
                rom[address : address + len(encoded)] = encoded
                remaining = max_bytes - len(encoded)
                if remaining > 0:
                    rom[address + len(encoded) : address + max_bytes] = (
                        b"\xFF" * remaining
                    )
                stats["in_place"] += 1
            elif safe_ptrs:
                # CRITICAL: Only relocate if ALL pointers are safe
                # If some pointers are unsafe, those would still point to the old
                # address after relocation, causing crashes
                if unsafe_count > 0:
                    stats["skipped_partial_ptrs"] += 1
                    continue

                # Relocate to free space
                if self.free_ptr + len(encoded) >= FONT_PATCH_BOUNDARY:
                    stats["skipped"] += 1
                    continue

                rom[self.free_ptr : self.free_ptr + len(encoded)] = encoded
                # Update all pointers (we verified all are safe above)
                for ptr_addr in safe_ptrs:
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
