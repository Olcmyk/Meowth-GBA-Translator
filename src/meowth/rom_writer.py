"""ROM writer for injecting translated text."""

import json
from pathlib import Path
from typing import Optional

from .charmap import Charmap, get_default_charmap
from .pcs_scanner import is_real_text


class RomWriter:
    """Writes translated text to GBA ROM with pointer redirection."""

    # Font patch boundary - don't write past this
    FONT_BOUNDARY = 0x01FD3000

    # Expansion area start
    EXPANSION_START = 0x01000000

    # GBA pointer offset
    POINTER_OFFSET = 0x08000000

    # Minimum safe pointer source for HMA-verified entries
    # HMA correctly identifies literal pool entries in code as pointer sources
    # We trust all HMA pointer sources (no brute-force scanning anymore)
    MIN_POINTER_SOURCE = 0x100000

    def __init__(self, charmap: Optional[Charmap] = None):
        self.charmap = charmap or get_default_charmap()
        self.write_offset = self.EXPANSION_START

    def inject(
        self,
        rom_path: str | Path,
        translations_path: str | Path,
        output_path: Optional[str | Path] = None,
    ) -> None:
        """Inject translated text into ROM.

        Args:
            rom_path: Path to source ROM
            translations_path: Path to translations JSON
            output_path: Path for output ROM (default: modify in place)
        """
        rom_path = Path(rom_path)
        translations_path = Path(translations_path)
        output_path = Path(output_path) if output_path else rom_path

        # Load ROM
        with open(rom_path, "rb") as f:
            rom = bytearray(f.read())

        # Load translations
        with open(translations_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", [])
        stats = {"written": 0, "skipped": 0, "skipped_garbage": 0, "skipped_same": 0, "errors": 0}

        for entry in entries:
            try:
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
        elif len(encoded) <= original_length:
            # In-place replacement (pad with 0xFF if shorter)
            self._write_in_place(rom, address, encoded, original_length, stats)
        else:
            # Text too long and no pointers - skip to preserve table structure
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
        """Write text in place, padding with 0xFF if needed."""
        if address + max_length > len(rom):
            stats["errors"] += 1
            return

        # Write encoded data
        write_len = min(len(encoded), max_length)
        rom[address : address + write_len] = encoded[:write_len]

        # Pad remaining space with 0xFF
        if write_len < max_length:
            rom[address + write_len : address + max_length] = b"\xFF" * (
                max_length - write_len
            )

        stats["written"] += 1

    def _truncate_encoded(self, encoded: bytes, max_length: int) -> bytes:
        """Truncate encoded text to fit max length, ensuring valid termination."""
        if len(encoded) <= max_length:
            return encoded

        # Find a safe truncation point (don't split 2-byte chars)
        truncated = bytearray(encoded[: max_length - 1])
        truncated.append(0xFF)  # Add terminator
        return bytes(truncated)
