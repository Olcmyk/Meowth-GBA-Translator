"""ROM writer for injecting translated text."""

import json
import os
from pathlib import Path
from typing import Optional

from .charmap import Charmap
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
    _MIN_RELOCATION_BLOCK = 4 * 1024

    _FIXED_WIDTH_TABLE_CATEGORIES = {
        "pokemon_names",
        "move_names",
        "ability_names",
        "nature_names",
        "type_names",
        "item_names",
        "berry_names",
        "decoration_names",
        "pokedex_species",
        "trainer_classes",
        "trainer_names",
        "trade_nicknames",
        "trade_trainer_names",
        "map_names",
        "habitat_names",
        "menu_options",
        "menu_pc",
        "menu_pcoptions",
        "menu_pokemon",
        "menu_item_storage",
        "menu_pause",
        "menu_pokemon_options",
    }

    def __init__(self, charmap: Optional[Charmap] = None, game: str = "firered", target_lang: str = "ko"):
        self.charmap = charmap or Charmap(target_lang=target_lang)
        self.target_lang = target_lang
        self.FONT_BOUNDARY = self._FONT_BOUNDARIES.get(game, 0x01FD3000)
        self.write_offset = self.EXPANSION_START  # updated in inject()
        self.write_limit = self.FONT_BOUNDARY
        self.free_blocks: list[list[int]] = []
        self._encoded_overrides: dict[str, bytes] = {}
        self.allow_text_slot_reclaim = os.environ.get("MEOWTH_ALLOW_TEXT_SLOT_RECLAIM") == "1"
        self.allow_implicit_pointer_search = (
            os.environ.get("MEOWTH_ALLOW_IMPLICIT_POINTER_SEARCH") == "1"
        )

    @staticmethod
    def _find_free_space(rom: bytes, boundary: int) -> tuple[int, int]:
        """Find the largest contiguous 0xFF block before boundary.

        Returns (start, end). The old implementation only used trailing free
        space adjacent to the font area; many 32MB hacks have usable gaps
        earlier in the expansion area, so scan for the largest safe block.
        """
        end = min(boundary, len(rom))
        start = min(RomWriter.EXPANSION_START, end)
        best_start = end
        best_end = end
        pos = start
        while pos < end:
            if rom[pos] != 0xFF:
                pos += 1
                continue
            block_start = pos
            while pos < end and rom[pos] == 0xFF:
                pos += 1
            if pos - block_start > best_end - best_start:
                best_start = block_start
                best_end = pos
        return best_start, best_end

    @staticmethod
    def _find_free_blocks(
        rom: bytes,
        start: int = EXPANSION_START,
        end: int | None = None,
        min_size: int = _MIN_RELOCATION_BLOCK,
    ) -> list[tuple[int, int]]:
        """Find large usable 0xFF blocks in expanded ROM space.

        ROM hacks often contain short 0xFF runs inside compressed graphics,
        tilemaps, or alignment padding. Treating those tiny runs as free text
        space corrupts maps. Only large contiguous blocks are considered safe.
        """
        blocks: list[tuple[int, int]] = []
        scan_end = min(end if end is not None else len(rom), len(rom))
        pos = min(start, scan_end)
        while pos < scan_end:
            if rom[pos] != 0xFF:
                pos += 1
                continue
            block_start = pos
            while pos < scan_end and rom[pos] == 0xFF:
                pos += 1
            if pos - block_start >= min_size:
                blocks.append((block_start, pos))
        blocks.sort(key=lambda block: block[1] - block[0], reverse=True)
        return blocks

    def _reset_free_blocks(self, rom: bytes) -> int:
        blocks = self._find_free_blocks(rom, end=self.FONT_BOUNDARY)
        self.free_blocks = [[start, end] for start, end in blocks]
        self._sort_free_blocks()
        if self.free_blocks:
            self.write_offset, self.write_limit = self.free_blocks[0]
        else:
            self.write_offset = self.write_limit = len(rom)
        return sum(end - start for start, end in blocks)

    def _sort_free_blocks(self) -> None:
        self.free_blocks.sort(key=lambda block: block[1] - block[0], reverse=True)

    def _add_free_block(self, start: int, end: int) -> None:
        if end - start < 16:
            return
        self.free_blocks.append([start, end])
        self._sort_free_blocks()

    def _actual_text_len(self, rom: bytes, address: int, max_length: int) -> int:
        actual_text_len = max_length
        for j in range(max_length):
            if address + j < len(rom) and rom[address + j] == 0xFF:
                actual_text_len = j + 1
                break
        return actual_text_len

    def _is_unsafe_extracted_entry(self, entry: dict) -> bool:
        haystack = " ".join(
            str(entry.get(key, ""))
            for key in ("category", "table_name", "table_field", "id")
        ).lower()
        unsafe_tokens = (
            "graphics", "gfx", "sprite", "sprites", "palette", "palettes",
            "tileset", "tilesets", "tilemap", "animation", "animations",
            "sound", "song", "songs", "cry", "cries", "music", "track",
            "tracks",
        )
        return any(token in haystack for token in unsafe_tokens)

    def _reclaim_relocated_text_slots(self, rom: bytes, entries: list[dict]) -> int:
        """Reuse old pointer-based text slots that will be redirected.

        Pointer-based text no longer needs its original bytes once every pointer
        source is updated to the relocated Korean string. Reclaiming these slots
        is required for full-game Korean builds where translated dialogue is
        substantially larger than the remaining 0xFF expansion space.
        """
        reclaimed: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for entry in entries:
            if self._is_unsafe_extracted_entry(entry):
                continue
            original = entry.get("original", "").strip('"')
            translated = entry.get("translated", "").strip('"')
            if entry.get("category") == "scripts" and not is_real_text(original):
                continue
            if not translated or translated == original:
                continue
            pointer_sources = entry.get("pointer_addresses", entry.get("pointer_sources", []))
            if not pointer_sources:
                continue
            address = int(entry.get("address", "0x0").replace("0x", ""), 16)
            original_length = int(entry.get("byte_length") or 0)
            if address < self.MIN_POINTER_SOURCE or original_length <= 0:
                continue
            try:
                encoded = self.charmap.encode(translated)
            except Exception:
                continue
            actual_text_len = self._actual_text_len(rom, address, original_length)
            if len(encoded) <= actual_text_len:
                continue
            block = (address, min(address + actual_text_len, len(rom)))
            if block not in seen:
                seen.add(block)
                reclaimed.append(block)

        for start, end in reclaimed:
            self._add_free_block(start, end)
        return sum(end - start for start, end in reclaimed)

    def _compact_korean_relocation_texts(
        self,
        rom: bytes,
        entries: list[dict],
        stats: dict,
    ) -> None:
        if self.target_lang != "ko":
            return

        candidates: list[tuple[dict, bytes]] = []
        for entry in entries:
            if self._is_unsafe_extracted_entry(entry):
                continue
            original = entry.get("original", "").strip('"')
            translated = entry.get("translated", "").strip('"')
            if entry.get("category") == "scripts" and not is_real_text(original):
                continue
            if not translated or translated == original:
                continue
            pointer_sources = entry.get("pointer_addresses", entry.get("pointer_sources", []))
            if not pointer_sources:
                continue
            address = int(entry.get("address", "0x0").replace("0x", ""), 16)
            original_length = int(entry.get("byte_length") or 0)
            if address <= 0 or original_length <= 0:
                continue
            try:
                encoded = self.charmap.encode(translated)
            except Exception:
                continue
            if len(encoded) <= self._actual_text_len(rom, address, original_length):
                continue
            candidates.append((entry, encoded))

        if not candidates:
            return

        available = sum(end - start for start, end in self.free_blocks)
        needed = sum(len(encoded) for _, encoded in candidates)
        reserve = min(32 * 1024, max(0, available // 10))
        budget = max(0, available - reserve)
        if needed <= budget:
            return

        min_cap = 8
        cap = max(min_cap, budget // len(candidates))
        while cap > min_cap and sum(min(len(encoded), cap) for _, encoded in candidates) > budget:
            cap -= 1

        compacted = 0
        saved = 0
        for entry, encoded in candidates:
            if len(encoded) <= cap:
                continue
            compacted_encoded = self._truncate_encoded(encoded, cap)
            entry_id = entry.get("id")
            if entry_id:
                self._encoded_overrides[entry_id] = compacted_encoded
            compacted += 1
            saved += len(encoded) - len(compacted_encoded)

        stats["compacted"] = compacted
        stats["compacted_saved"] = saved
        if compacted:
            print(
                f"Compacted {compacted:,} Korean relocated texts to fit ROM space "
                f"(saved {saved:,} bytes; cap {cap} bytes)"
            )

    def _allocate_relocation_space(self, size: int) -> int:
        for block in self.free_blocks:
            start, end = block
            if start + size <= end:
                block[0] = start + size
                self.write_offset = block[0]
                self.write_limit = end
                return start
        raise RuntimeError(f"No free ROM block large enough for {size} bytes")

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

        # Auto-detect safe expansion blocks (avoid overwriting hack/font data)
        available = self._reset_free_blocks(rom)
        if available < self._MIN_FREE_BLOCK:
            print(f"Warning: only {available:,} bytes free for redirected text")
        first = self.free_blocks[0] if self.free_blocks else [0, 0]
        print(
            f"Expansion region start: 0x{first[0]:08X} "
            f"({available:,} bytes available across {len(self.free_blocks)} blocks)"
        )

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
            capacity = original_length if self._is_fixed_width_table(entry) else actual_text_len
            if len(encoded) <= capacity:
                self._write_in_place(rom, address, encoded, original_length, stats)
            else:
                if self._is_fixed_width_table(entry):
                    stats["skipped_same"] += 1
                    return
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
        try:
            target = self._allocate_relocation_space(len(encoded))
        except RuntimeError as e:
            print(f"Warning: {e}")
            stats["errors"] += 1
            return

        # Ensure ROM is large enough
        if target + len(encoded) > len(rom):
            stats["errors"] += 1
            return

        # Write encoded text
        rom[target : target + len(encoded)] = encoded

        # Update all pointers (skip false positives in code section)
        new_pointer = self.POINTER_OFFSET + target
        for ptr_src in pointer_sources:
            ptr_addr = int(ptr_src.replace("0x", ""), 16)
            if ptr_addr < self.MIN_POINTER_SOURCE:
                continue  # Skip: likely machine code, not a real pointer
            if ptr_addr + 4 <= len(rom):
                rom[ptr_addr : ptr_addr + 4] = new_pointer.to_bytes(4, "little")

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

    def _search_pointers(self, rom: bytearray, target_address: int) -> list[str]:
        """Search ROM for pointers to the given address.

        Returns list of pointer source addresses in hex format (e.g., "0x00120674").
        Only searches in safe data section (>= MIN_POINTER_SOURCE).
        """
        pointer_value = (self.POINTER_OFFSET + target_address).to_bytes(4, "little")
        found = []

        # Search from MIN_POINTER_SOURCE to FONT_BOUNDARY
        search_end = min(self.FONT_BOUNDARY, len(rom) - 4)
        for addr in range(self.MIN_POINTER_SOURCE, search_end, 4):  # Align to 4 bytes
            if rom[addr:addr+4] == pointer_value:
                found.append(f"0x{addr:08X}")

        return found

    def _write_relocated(
        self, rom: bytearray, encoded: bytes, pointer_sources: list
    ) -> None:
        """Write text to expansion area and update pointers (no stats)."""
        target = self._allocate_relocation_space(len(encoded))
        if target + len(encoded) > len(rom):
            raise RuntimeError("ROM too small for relocated text")

        rom[target : target + len(encoded)] = encoded
        new_pointer = self.POINTER_OFFSET + target
        for ptr_src in pointer_sources:
            ptr_addr = int(ptr_src.replace("0x", ""), 16)
            if ptr_addr < self.MIN_POINTER_SOURCE:
                continue
            if ptr_addr + 4 <= len(rom):
                rom[ptr_addr : ptr_addr + 4] = new_pointer.to_bytes(4, "little")

    def _write_relocated_v2(
        self,
        rom: bytearray,
        encoded: bytes,
        pointer_sources: list,
        stats: dict,
    ) -> None:
        try:
            self._write_relocated(rom, encoded, pointer_sources)
            stats["relocated"] += 1
            return
        except RuntimeError:
            if self.target_lang != "ko":
                raise

        max_block = max((end - start for start, end in self.free_blocks), default=0)
        if max_block < 2:
            raise RuntimeError("No free ROM block left for compacted Korean text")
        compacted = self._truncate_encoded(encoded, max_block)
        self._write_relocated(rom, compacted, pointer_sources)
        stats["relocated"] += 1
        stats["compacted"] = stats.get("compacted", 0) + 1
        stats["compacted_saved"] = stats.get("compacted_saved", 0) + (
            len(encoded) - len(compacted)
        )

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
        - Font patch Chinese chars (high bytes 0x01-0x1E excl 0x06/0x1B) — CJK only
        - FC/FD control codes with argument bytes
        """
        if len(encoded) <= max_length:
            return encoded

        from .languages import is_cjk_language
        is_cjk = is_cjk_language(self.target_lang)

        # Walk through encoded bytes respecting multi-byte boundaries
        i = 0
        while i < max_length - 1:  # leave room for 0xFF terminator
            b = encoded[i]
            if b == 0xFF:
                break
            # Font patch 2-byte Chinese character (only for CJK languages)
            if is_cjk and b in self._CHINESE_HIGH_BYTES:
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
        # Auto-detect safe expansion blocks
        available = self._reset_free_blocks(rom)
        if available < self._MIN_FREE_BLOCK:
            print(f"Warning: only {available:,} bytes free for redirected text")
        first = self.free_blocks[0] if self.free_blocks else [0, 0]
        print(
            f"Expansion region start: 0x{first[0]:08X} "
            f"({available:,} bytes available across {len(self.free_blocks)} blocks)"
        )

        stats = {
            "in_place": 0, "relocated": 0, "skipped": 0,
            "skipped_garbage": 0, "skipped_unsafe": 0, "skipped_same": 0,
            "skipped_no_address": 0, "skipped_fixed_too_long": 0,
            "skipped_partial_ptrs": 0, "unsafe_ptrs": 0,
            "skipped_binary_table": 0, "errors": 0,
            "reclaimed": 0, "compacted": 0, "compacted_saved": 0,
        }

        reclaimed = self._reclaim_relocated_text_slots(rom, entries) if self.allow_text_slot_reclaim else 0
        stats["reclaimed"] = reclaimed
        if reclaimed:
            total_available = sum(end - start for start, end in self.free_blocks)
            print(
                f"Reclaimed {reclaimed:,} bytes from old pointer text slots "
                f"({total_available:,} bytes total available)"
            )
        self._encoded_overrides = {}
        self._compact_korean_relocation_texts(rom, entries, stats)

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
        if self._is_unsafe_extracted_entry(entry):
            stats["skipped"] += 1
            stats["skipped_binary_table"] += 1
            return
        if entry.get("category") == "scripts" and not is_real_text(original):
            stats["skipped"] += 1
            stats["skipped_garbage"] += 1
            return

        address = int(entry.get("address", "0x0").replace("0x", ""), 16)
        pointer_sources = entry.get("pointer_addresses", entry.get("pointer_sources", []))

        # Defense-in-depth: never write in-place to the ARM code section
        if address < self.MIN_POINTER_SOURCE and not pointer_sources:
            stats["skipped"] += 1
            stats["skipped_unsafe"] += 1
            return

        if not translated or translated == original:
            stats["skipped"] += 1
            stats["skipped_same"] += 1
            return

        try:
            encoded = self._encoded_overrides.get(entry.get("id"))
            if encoded is None:
                encoded = self.charmap.encode(translated)
        except Exception as e:
            print(f"Encoding error for {entry.get('id', '?')}: {e}")
            stats["errors"] += 1
            return

        is_pointer_based = entry.get("is_pointer_based", bool(pointer_sources))
        original_length = entry.get("byte_length", 0)

        if is_pointer_based and pointer_sources:
            actual_text_len = self._actual_text_len(rom, address, original_length) if original_length else 0
            if address > 0 and original_length > 0 and len(encoded) <= actual_text_len:
                self._write_in_place_v2(rom, address, encoded, original_length)
                stats["in_place"] += 1
            else:
                self._write_relocated_v2(rom, encoded, pointer_sources, stats)
        elif address > 0 and original_length > 0:
            actual_text_len = self._actual_text_len(rom, address, original_length)
            capacity = original_length if self._is_fixed_width_table(entry) else actual_text_len
            if len(encoded) <= capacity:
                self._write_in_place_v2(rom, address, encoded, original_length)
                stats["in_place"] += 1
            else:
                if self._is_fixed_width_table(entry):
                    if self.target_lang == "ko":
                        compacted = self._truncate_encoded(encoded, capacity)
                        self._write_in_place_v2(rom, address, compacted, original_length)
                        stats["in_place"] += 1
                        stats["compacted"] = stats.get("compacted", 0) + 1
                        stats["compacted_saved"] = stats.get("compacted_saved", 0) + (
                            len(encoded) - len(compacted)
                        )
                        return
                    stats["skipped"] += 1
                    stats["skipped_fixed_too_long"] += 1
                    return
                # Do not infer pointer sources by scanning arbitrary ROM data.
                # Hacks often contain binary values that look like GBA pointers;
                # rewriting those is what makes unrelated screens show the
                # wrong text. Only explicitly extracted pointer sources may be
                # redirected. An opt-in env var keeps the old behavior available
                # for debugging known-safe ROMs.
                found_pointers = (
                    self._search_pointers(rom, address)
                    if self.allow_implicit_pointer_search
                    else []
                )
                if found_pointers:
                    self._write_relocated_v2(rom, encoded, found_pointers, stats)
                    return

                truncated = self._truncate_encoded(encoded, actual_text_len)
                self._write_in_place_v2(rom, address, truncated, original_length)
                stats["in_place"] += 1
        else:
            stats["skipped"] += 1
            stats["skipped_no_address"] += 1

    def _is_fixed_width_table(self, entry: dict) -> bool:
        """Return True for table fields that must not be truncated."""
        category = entry.get("category", "")
        if category in self._FIXED_WIDTH_TABLE_CATEGORIES:
            return True
        return bool(entry.get("table_name")) and not entry.get("pointer_sources")
