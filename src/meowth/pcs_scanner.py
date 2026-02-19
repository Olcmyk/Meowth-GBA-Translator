"""Brute-force PCS text scanner to find texts HMA missed.

HMA's model.All<PCSRun>() only finds ~3143 texts because it only creates PCSRun
objects for pointer targets discovered by its metadata model. Script-embedded
pointers at non-aligned offsets are missed entirely.

This scanner finds ALL GBA pointers in the ROM, validates their targets as PCS
strings, and merges the results with HMA's extraction.
"""

import struct
from pathlib import Path

from .pcs_codes import (
    CONTROL_CODE_PREFIX,
    ESCAPE_PREFIX,
    F7_PREFIX,
    F9_PREFIX,
    BUTTON_PREFIX,
    LINE_SCROLL,
    NEWLINE,
    PARAGRAPH,
    TERMINATOR,
    FC_MACROS,
    FD_MACROS,
    F9_MACROS,
    PCS_CHAR_TABLE,
    VALID_PCS_BYTES,
    fc_arg_count,
)

GBA_ROM_BASE = 0x08000000

class PCSScanner:
    """Scan ROM for PCS text strings referenced by pointers."""

    def __init__(self, rom: bytes, rom_size_original: int = 0x01000000):
        self.rom = rom
        self.rom_size = rom_size_original

    def scan_pointers(self) -> dict[int, list[int]]:
        """Find all GBA pointers in the original ROM area.

        Scans every byte offset (not just aligned) because script commands
        like loadpointer (0x0F) embed pointers at non-aligned offsets.

        Returns: {destination_rom_offset: [source_offsets...]}
        """
        rom = self.rom
        size = self.rom_size
        lo = GBA_ROM_BASE
        hi = GBA_ROM_BASE + size
        targets: dict[int, list[int]] = {}

        for i in range(size - 3):
            val = struct.unpack_from("<I", rom, i)[0]
            if lo <= val < hi:
                dest = val - GBA_ROM_BASE
                if dest in targets:
                    targets[dest].append(i)
                else:
                    targets[dest] = [i]

        return targets

    def read_pcs_string(self, offset: int) -> tuple[str, int] | None:
        """Try to read a PCS-encoded string at the given ROM offset.

        Returns (decoded_text, byte_length) or None if not a valid PCS string.
        """
        rom = self.rom
        rom_len = len(rom)
        parts: list[str] = []
        i = offset
        repeat_count = 0
        last_byte = -1
        space_count = 0
        total_bytes = 0

        while i < rom_len:
            b = rom[i]

            # Terminator (0xFF)
            if b == TERMINATOR:
                total_bytes = i - offset
                break

            # Track repeats
            if b == last_byte:
                repeat_count += 1
                if repeat_count > 3:
                    return None
            else:
                repeat_count = 0
                last_byte = b

            # Newline (0xFE)
            if b == NEWLINE:
                parts.append("\n")
                i += 1
                continue

            # Paragraph wait (0xFB)
            if b == PARAGRAPH:
                parts.append("\n\n")
                i += 1
                continue

            # Line scroll (0xFA)
            if b == LINE_SCROLL:
                parts.append("\\l")
                i += 1
                continue

            # FC control code
            if b == CONTROL_CODE_PREFIX:
                if i + 1 >= rom_len:
                    return None
                cmd = rom[i + 1]
                n_args = fc_arg_count(cmd)
                total_skip = 2 + n_args  # FC + cmd + args
                if i + total_skip > rom_len:
                    return None
                # Decode to HMA representation
                if n_args == 0 and cmd in FC_MACROS:
                    parts.append(FC_MACROS[cmd])
                else:
                    hex_str = "".join(f"{rom[i+1+j]:02X}" for j in range(1 + n_args))
                    parts.append(f"\\CC{hex_str}")
                i += total_skip
                continue

            # FD escape
            if b == ESCAPE_PREFIX:
                if i + 1 >= rom_len:
                    return None
                val = rom[i + 1]
                if val in FD_MACROS:
                    parts.append(FD_MACROS[val])
                else:
                    parts.append(f"\\\\{val:02X}")
                i += 2
                continue

            # F7 escape
            if b == F7_PREFIX:
                if i + 1 >= rom_len:
                    return None
                parts.append(f"\\?{rom[i+1]:02X}")
                i += 2
                continue

            # F8 button escape
            if b == BUTTON_PREFIX:
                if i + 1 >= rom_len:
                    return None
                parts.append(f"\\btn{rom[i+1]:02X}")
                i += 2
                continue

            # F9 macro
            if b == F9_PREFIX:
                if i + 1 >= rom_len:
                    return None
                val = rom[i + 1]
                if val in F9_MACROS:
                    parts.append(F9_MACROS[val])
                else:
                    parts.append(f"\\9{val:02X}")
                i += 2
                continue

            # Regular PCS character
            if b in VALID_PCS_BYTES:
                ch = PCS_CHAR_TABLE[b]
                parts.append(ch)
                if b == 0x00:
                    space_count += 1
                i += 1
                continue

            # Invalid byte
            return None
        else:
            # Ran off end of ROM without terminator
            return None

        if total_bytes == 0:
            return None

        # Reject >50% spaces
        if total_bytes > 0 and space_count / total_bytes > 0.5:
            return None

        text = "".join(parts)
        return text, total_bytes

    def scan(self, min_length: int = 2) -> list[dict]:
        """Full scan: find pointers, validate PCS strings, filter quality.

        Returns list of dicts with id, address, pointer_addresses, original, byte_length.
        """
        print("  Scanning ROM for GBA pointers...")
        targets = self.scan_pointers()
        print(f"  Found {len(targets)} unique pointer targets")

        print("  Validating PCS strings...")
        results: list[dict] = []
        for dest_offset in sorted(targets):
            result = self.read_pcs_string(dest_offset)
            if result is None:
                continue
            text, byte_len = result
            if byte_len < min_length:
                continue
            if not self._quality_check(text):
                continue
            results.append({
                "address": f"0x{dest_offset:06X}",
                "pointer_addresses": [f"0x{s:06X}" for s in targets[dest_offset]],
                "original": text,
                "byte_length": byte_len,
            })

        print(f"  Found {len(results)} valid PCS strings")
        return results

    @staticmethod
    def _quality_check(text: str) -> bool:
        """Filter out binary data masquerading as text."""
        if len(text) < 4:
            return False
        # Must have at least one lowercase letter
        if not any("a" <= c <= "z" for c in text):
            return False
        # Must have at least one space
        if " " not in text:
            return False
        # >40% ASCII letters/digits/space
        ascii_count = sum(
            1 for c in text
            if ("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9") or c == " "
        )
        if ascii_count / len(text) < 0.4:
            return False
        return True

    @staticmethod
    def merge_with_hma(hma_data: dict, scanned: list[dict]) -> dict:
        """Merge scanned texts into HMA extraction data.

        - Texts at addresses already in HMA: merge pointer_addresses (union)
        - New texts: add to free_texts with scan_NNNNN IDs
        """
        # Build set of known addresses from HMA data
        known_addrs: dict[str, dict] = {}
        for table in hma_data.get("tables", []):
            for entry in table.get("entries", []):
                known_addrs[entry["address"]] = entry
        for entry in hma_data.get("free_texts", []):
            known_addrs[entry["address"]] = entry

        new_count = 0
        merged_count = 0
        for item in scanned:
            addr = item["address"]
            if addr in known_addrs:
                # Merge pointer addresses
                existing = known_addrs[addr]
                existing_ptrs = set(existing.get("pointer_addresses", []))
                new_ptrs = set(item["pointer_addresses"])
                merged = existing_ptrs | new_ptrs
                existing["pointer_addresses"] = sorted(merged)
                merged_count += 1
            else:
                new_count += 1
                item["id"] = f"scan_{new_count:05d}"
                hma_data.setdefault("free_texts", []).append(item)

        print(f"  Merge: {new_count} new texts, {merged_count} pointer updates")
        return hma_data


def scan_and_merge(rom_path: Path, texts_path: Path) -> Path:
    """Run PCS scan on ROM and merge results into texts.json.

    Args:
        rom_path: Path to original ROM file
        texts_path: Path to HMA-extracted texts.json (modified in place)

    Returns:
        texts_path (same file, updated)
    """
    import json

    rom = rom_path.read_bytes()
    scanner = PCSScanner(rom)
    scanned = scanner.scan()

    data = json.loads(texts_path.read_text(encoding="utf-8"))
    hma_free_count = len(data.get("free_texts", []))
    data = scanner.merge_with_hma(data, scanned)
    total_free = len(data.get("free_texts", []))

    texts_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  texts.json: {hma_free_count} → {total_free} free texts")
    return texts_path
