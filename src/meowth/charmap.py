"""Parse Pokemon_GBA_Font_Patch charmap and provide encoding/decoding."""

from pathlib import Path

# Default charmap path
DEFAULT_CHARMAP = Path(__file__).parent.parent.parent / "Pokemon_GBA_Font_Patch" / "pokeFRLG" / "PMRSEFRLG_charmap.txt"


class Charmap:
    def __init__(self, charmap_path: Path = DEFAULT_CHARMAP):
        self.char_to_bytes: dict[str, bytes] = {}
        self.bytes_to_char: dict[int, str] = {}
        self._parse(charmap_path)

    def _parse(self, path: Path):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            hex_part, char_part = line.split("=", 1)
            hex_val = int(hex_part.strip(), 16)

            if not char_part:
                char_part = " "  # 0x00 = space

            if hex_val <= 0xFF:
                self.char_to_bytes[char_part] = bytes([hex_val])
                self.bytes_to_char[hex_val] = char_part
            else:
                hi = (hex_val >> 8) & 0xFF
                lo = hex_val & 0xFF
                self.char_to_bytes[char_part] = bytes([hi, lo])
                self.bytes_to_char[hex_val] = char_part

    def encode_char(self, ch: str) -> bytes | None:
        """Encode a single character to Font Patch bytes."""
        return self.char_to_bytes.get(ch)

    def encode_string(self, text: str) -> bytearray:
        """Encode a string to Font Patch bytes. Raises ValueError for unsupported chars."""
        result = bytearray()
        i = 0
        while i < len(text):
            ch = text[i]
            encoded = self.encode_char(ch)
            if encoded is None:
                raise ValueError(f"Character '{ch}' (U+{ord(ch):04X}) not in charmap")
            result.extend(encoded)
            i += 1
        return result

    def can_encode(self, text: str) -> tuple[bool, list[str]]:
        """Check if all characters in text can be encoded. Returns (ok, bad_chars)."""
        bad = [ch for ch in text if ch not in self.char_to_bytes]
        return len(bad) == 0, bad

    def supported_chars(self) -> set[str]:
        """Return set of all supported characters."""
        return set(self.char_to_bytes.keys())

    def byte_length(self, text: str) -> int:
        """Calculate the byte length of encoded text (without terminator)."""
        length = 0
        for ch in text:
            enc = self.encode_char(ch)
            if enc:
                length += len(enc)
            else:
                length += 1  # assume 1 byte for unknown
        return length
