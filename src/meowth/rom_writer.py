"""ROM writer for injecting translated text."""

import json
from pathlib import Path
from typing import Optional

from .charmap import Charmap, get_default_charmap
from .pcs_scanner import is_real_text


class RomWriter:
    """Writes translated text to GBA ROM with pointer redirection."""

    # Per-game font patch boundaries (ROM offset where font data begins)
    _FONT_BOUNDARIES: dict[str, int] = {
        "firered": 0x01FD3000,
        "leafgreen": 0x01FD3000,
        "emerald": 0x01FD0000,  # HackFunctionAddresses 0x09FD0000 - 0x08000000
    }

    # Default for backwards compatibility
    FONT_BOUNDARY = 0x01FD3000

    # Fallback expansion start (vanilla FireRed only; hacks use more space)
    EXPANSION_START = 0x01000000

    # GBA pointer offset
    POINTER_OFFSET = 0x08000000

    # Minimum safe pointer source address.
    # ARM code section ends around 0x0A0000 in FRLG/Emerald.  Pointer sources
    # inside the code section are literal-pool entries that look like
    # pointers but are actually ARM instructions — writing to them
    # corrupts the executable code and crashes the game.
    MIN_POINTER_SOURCE = 0x0A0000

    # Minimum contiguous free block required (bytes)
    _MIN_FREE_BLOCK = 512 * 1024  # 512 KB

    def __init__(self, charmap: Optional[Charmap] = None, game: str = "firered"):
        self.charmap = charmap or get_default_charmap()
        self.FONT_BOUNDARY = self._FONT_BOUNDARIES.get(game, 0x01FD3000)
        self.write_offset = self.EXPANSION_START  # updated in inject()

    @staticmethod
    def _find_free_space(rom: bytes, boundary: int) -> int:
        """Find the start of the largest contiguous 0xFF block before boundary.

        Scans backwards from *boundary* to locate free space that ROM hacks
        haven't used.  Returns the offset of the first byte of that block.
        """
        end = min(boundary, len(rom))
        pos = end - 1
        while pos >= 0 and rom[pos] == 0xFF:
            pos -= 1
        # pos is now the last non-FF byte; free space starts right after
        return pos + 1

    def inject(
        self,
        rom_path: str | Path,
        translations_path: str | Path,
        output_path: Optional[str | Path] = None,
        overrides: Optional[dict[str, str]] = None,
    ) -> None:
        """Inject translated text into ROM.

        Args:
            rom_path: Path to source ROM
            translations_path: Path to translations JSON
            output_path: Path for output ROM (default: modify in place)
            overrides: Optional dict of entry_id -> hardcoded translation
        """
        rom_path = Path(rom_path)
        translations_path = Path(translations_path)
        output_path = Path(output_path) if output_path else rom_path

        # Load ROM
        with open(rom_path, "rb") as f:
            rom = bytearray(f.read())

        # Auto-detect safe expansion start (avoid overwriting hack data)
        free_start = self._find_free_space(rom, self.FONT_BOUNDARY)
        available = self.FONT_BOUNDARY - free_start
        if available < self._MIN_FREE_BLOCK:
            print(f"Warning: only {available:,} bytes free before font boundary")
        self.write_offset = free_start
        print(f"扩展区起始: 0x{free_start:08X} (可用 {available:,} 字节)")

        # Load translations
        with open(translations_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", [])
        stats = {"written": 0, "skipped": 0, "skipped_garbage": 0, "skipped_same": 0, "errors": 0}

        for entry in entries:
            try:
                # Apply hardcoded overrides if provided
                if overrides and entry.get("id") in overrides:
                    entry["translated"] = overrides[entry["id"]]
                self._process_entry(rom, entry, stats)
            except Exception as e:
                print(f"Error processing {entry.get('id', '?')}: {e}")
                stats["errors"] += 1

        # Write output
        with open(output_path, "wb") as f:
            f.write(rom)

        print(f"写入完成: {stats['written']} 条写入, {stats['skipped_same']} 条未变, {stats['skipped_garbage']} 条垃圾跳过, {stats['errors']} 错误")

    def _process_entry(self, rom: bytearray, entry: dict, stats: dict) -> None:
        """Process a single text entry."""
        original = entry.get("original", "")
        translated = entry.get("translated", "")

        # Safety check: skip if original looks like garbage (not real text)
        if entry.get("category") == "scripts" and not is_real_text(original):
            stats["skipped_garbage"] += 1
            return

        address = int(entry.get("address", "0x0").replace("0x", ""), 16)
        entry_id = entry.get("id", "")
        pointer_sources = entry.get("pointer_sources", [])

        # Defense-in-depth: never write in-place to the ARM code section
        if address < self.MIN_POINTER_SOURCE and not pointer_sources:
            stats["skipped_same"] += 1
            return

        # Skip if no translation or same as original
        if not translated or translated == original:
            stats["skipped_same"] += 1
            return

        # Clean text (remove HMA quotes)
        clean_translated = translated.strip('"')
        if not clean_translated:
            stats["skipped_same"] += 1
            return

        # Encode text
        try:
            encoded = self.charmap.encode(clean_translated)
        except Exception as e:
            print(f"Encoding error for {entry.get('id', '?')}: {e}")
            stats["errors"] += 1
            return

        is_pointer_based = entry.get("is_pointer_based", False)
        original_length = entry.get("byte_length", 0)

        # Decide write strategy
        if is_pointer_based and pointer_sources:
            # Write to expansion area and update pointers
            self._write_with_redirect(rom, encoded, pointer_sources, stats)
        elif address > 0 and original_length > 0:
            # In-place: find actual text footprint (up to first 0xFF)
            actual_text_len = original_length
            for j in range(original_length):
                if address + j < len(rom) and rom[address + j] == 0xFF:
                    actual_text_len = j + 1  # include terminator
                    break
            if len(encoded) <= actual_text_len:
                self._write_in_place(rom, address, encoded, original_length, stats)
            else:
                # Truncate to fit the original text slot
                truncated = self._truncate_encoded(encoded, actual_text_len)
                self._write_in_place(rom, address, truncated, original_length, stats)
        else:
            stats["skipped_same"] += 1

    def _write_with_redirect(
        self, rom: bytearray, encoded: bytes, pointer_sources: list, stats: dict
    ) -> None:
        """Write text to expansion area and update pointers."""
        # Check boundary
        if self.write_offset + len(encoded) >= self.FONT_BOUNDARY:
            print(f"Warning: Approaching font boundary at 0x{self.write_offset:X}")
            stats["errors"] += 1
            return

        # Ensure ROM is large enough
        if self.write_offset + len(encoded) > len(rom):
            stats["errors"] += 1
            return

        # Write encoded text
        rom[self.write_offset : self.write_offset + len(encoded)] = encoded

        # Update all pointers (skip false positives in code section)
        new_pointer = self.POINTER_OFFSET + self.write_offset
        for ptr_src in pointer_sources:
            ptr_addr = int(ptr_src.replace("0x", ""), 16)
            if ptr_addr < self.MIN_POINTER_SOURCE:
                continue  # Skip: likely machine code, not a real pointer
            if ptr_addr + 4 <= len(rom):
                rom[ptr_addr : ptr_addr + 4] = new_pointer.to_bytes(4, "little")

        self.write_offset += len(encoded)
        stats["written"] += 1

    def _write_in_place(
        self, rom: bytearray, address: int, encoded: bytes, max_length: int, stats: dict
    ) -> None:
        """Write text in place, padding only up to the original text end.

        ``max_length`` from HMA may cover the entire data structure (e.g. 44
        bytes for an item entry where only the first 14 are the name).  We
        must NOT pad beyond the original text's 0xFF terminator, or we will
        destroy adjacent fields (price, effect, description pointer …).
        """
        if address + max_length > len(rom):
            stats["errors"] += 1
            return

        # Find the actual end of the original text (first 0xFF byte)
        orig_text_end = max_length
        for j in range(max_length):
            if rom[address + j] == 0xFF:
                orig_text_end = j + 1  # include the terminator itself
                break

        # Only write within the original text footprint
        safe_length = min(max_length, max(orig_text_end, len(encoded)))

        write_len = min(len(encoded), safe_length)
        rom[address : address + write_len] = encoded[:write_len]

        # Pad only up to the original text boundary (not the full struct)
        if write_len < orig_text_end:
            rom[address + write_len : address + orig_text_end] = b"\xFF" * (
                orig_text_end - write_len
            )

        stats["written"] += 1

    def _write_relocated(
        self, rom: bytearray, encoded: bytes, pointer_sources: list
    ) -> None:
        """Write text to expansion area and update pointers (no stats)."""
        if self.write_offset + len(encoded) >= self.FONT_BOUNDARY:
            raise RuntimeError(f"Approaching font boundary at 0x{self.write_offset:X}")
        if self.write_offset + len(encoded) > len(rom):
            raise RuntimeError("ROM too small for relocated text")

        rom[self.write_offset : self.write_offset + len(encoded)] = encoded
        new_pointer = self.POINTER_OFFSET + self.write_offset
        for ptr_src in pointer_sources:
            ptr_addr = int(ptr_src.replace("0x", ""), 16)
            if ptr_addr < self.MIN_POINTER_SOURCE:
                continue
            if ptr_addr + 4 <= len(rom):
                rom[ptr_addr : ptr_addr + 4] = new_pointer.to_bytes(4, "little")
        self.write_offset += len(encoded)

    def _write_in_place_v2(
        self, rom: bytearray, address: int, encoded: bytes, max_length: int
    ) -> None:
        """Write text in place (no stats). Raises on error."""
        if address + max_length > len(rom):
            raise RuntimeError(f"Address 0x{address:X} + {max_length} exceeds ROM")

        orig_text_end = max_length
        for j in range(max_length):
            if rom[address + j] == 0xFF:
                orig_text_end = j + 1
                break

        safe_length = min(max_length, max(orig_text_end, len(encoded)))
        write_len = min(len(encoded), safe_length)
        rom[address : address + write_len] = encoded[:write_len]

        if write_len < orig_text_end:
            rom[address + write_len : address + orig_text_end] = b"\xFF" * (
                orig_text_end - write_len
            )

    # Font patch Chinese character high bytes: 0x01-0x1E excluding 0x06, 0x1B
    _CHINESE_HIGH_BYTES = (
        set(range(0x01, 0x06)) | set(range(0x07, 0x1B)) | set(range(0x1C, 0x1F))
    )

    def _truncate_encoded(self, encoded: bytes, max_length: int) -> bytes:
        """Truncate encoded text to fit max length, ensuring valid termination.

        Respects multi-byte boundaries for:
        - Font patch Chinese chars (high bytes 0x01-0x1E excl 0x06/0x1B)
        - FC/FD control codes with argument bytes
        """
        if len(encoded) <= max_length:
            return encoded

        # Walk through encoded bytes respecting multi-byte boundaries
        i = 0
        while i < max_length - 1:  # leave room for 0xFF terminator
            b = encoded[i]
            if b == 0xFF:
                break
            # Font patch 2-byte Chinese character
            if b in self._CHINESE_HIGH_BYTES:
                if i + 2 > max_length - 1:
                    break  # not enough room for this char + terminator
                i += 2
            elif b == 0xFC:
                # FC control code: FC + cmd + args, skip all
                i += 2  # at minimum FC + 1 byte
                if i < len(encoded) and encoded[i-1] in (0x01, 0x04, 0x06):
                    i += 1  # extra arg byte
            elif b == 0xFD:
                i += 2  # FD + 1 byte
            else:
                i += 1

        truncated = bytearray(encoded[:i])
        truncated.append(0xFF)
        return bytes(truncated)

    # ------------------------------------------------------------------
    # High-level API used by Pipeline.build_rom
    # ------------------------------------------------------------------

    @staticmethod
    def load_rom(path: Path) -> bytearray:
        """Load a ROM file into a mutable bytearray."""
        return bytearray(Path(path).read_bytes())

    @staticmethod
    def expand_rom(rom: bytearray, target_size: int = 0x02000000) -> bytearray:
        """Expand ROM to target size (default 32MB) by padding with 0xFF."""
        if len(rom) < target_size:
            rom.extend(b"\xFF" * (target_size - len(rom)))
        return rom

    @staticmethod
    def save_rom(rom: bytearray, path: Path) -> None:
        """Write ROM bytearray to file."""
        Path(path).write_bytes(rom)

    def inject_texts(
        self,
        rom: bytearray,
        entries: list[dict],
        overrides: Optional[dict[str, str]] = None,
    ) -> tuple[bytearray, dict]:
        """Inject translated entries directly into a ROM bytearray.

        Returns (rom, stats).
        """
        # Auto-detect safe expansion start
        free_start = self._find_free_space(rom, self.FONT_BOUNDARY)
        available = self.FONT_BOUNDARY - free_start
        if available < self._MIN_FREE_BLOCK:
            print(f"Warning: only {available:,} bytes free before font boundary")
        self.write_offset = free_start
        print(f"扩展区起始: 0x{free_start:08X} (可用 {available:,} 字节)")

        stats = {
            "in_place": 0, "relocated": 0, "skipped": 0,
            "skipped_partial_ptrs": 0, "unsafe_ptrs": 0, "errors": 0,
        }

        for entry in entries:
            try:
                if overrides and entry.get("id") in overrides:
                    entry["translated"] = overrides[entry["id"]]
                self._process_entry_v2(rom, entry, stats)
            except Exception as e:
                print(f"Error processing {entry.get('id', '?')}: {e}")
                stats["errors"] += 1

        return rom, stats

    def _process_entry_v2(self, rom: bytearray, entry: dict, stats: dict) -> None:
        """Process a single entry for inject_texts (uses different stat keys)."""
        original = entry.get("original", "").strip('"')
        translated = entry.get("translated", "").strip('"')

        # Skip garbage entries (binary data misidentified as text)
        if entry.get("category") == "scripts" and not is_real_text(original):
            stats["skipped"] += 1
            return

        address = int(entry.get("address", "0x0").replace("0x", ""), 16)
        pointer_sources = entry.get("pointer_addresses", entry.get("pointer_sources", []))

        # Defense-in-depth: never write in-place to the ARM code section
        if address < self.MIN_POINTER_SOURCE and not pointer_sources:
            stats["skipped"] += 1
            return

        if not translated or translated == original:
            stats["skipped"] += 1
            return

        try:
            encoded = self.charmap.encode(translated)
        except Exception as e:
            print(f"Encoding error for {entry.get('id', '?')}: {e}")
            stats["errors"] += 1
            return

        is_pointer_based = entry.get("is_pointer_based", bool(pointer_sources))
        original_length = entry.get("byte_length", 0)

        if is_pointer_based and pointer_sources:
            self._write_relocated(rom, encoded, pointer_sources)
            stats["relocated"] += 1
        elif address > 0 and original_length > 0:
            actual_text_len = original_length
            for j in range(original_length):
                if address + j < len(rom) and rom[address + j] == 0xFF:
                    actual_text_len = j + 1
                    break
            if len(encoded) <= actual_text_len:
                self._write_in_place_v2(rom, address, encoded, original_length)
                stats["in_place"] += 1
            else:
                truncated = self._truncate_encoded(encoded, actual_text_len)
                self._write_in_place_v2(rom, address, truncated, original_length)
                stats["in_place"] += 1
        else:
            stats["skipped"] += 1
