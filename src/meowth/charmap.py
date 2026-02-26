"""Parse Pokemon_GBA_Font_Patch charmap and provide encoding/decoding."""

from pathlib import Path

from .languages import postprocess_for_language

# Default charmap path
DEFAULT_CHARMAP = Path(__file__).parent.parent.parent / "Pokemon_GBA_Font_Patch" / "pokeFRLG" / "PMRSEFRLG_charmap.txt"


class Charmap:
    def __init__(self, charmap_path: Path = DEFAULT_CHARMAP, target_lang: str = "zh-Hans"):
        self.char_to_bytes: dict[str, bytes] = {}
        self.bytes_to_char: dict[int, str] = {}
        self.target_lang = target_lang
        self._parse(charmap_path)

    def _parse(self, path: Path):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            hex_part, char_part = line.split("=", 1)
            hex_val = int(hex_part.strip(), 16)

            if not char_part:
                if hex_val == 0x00:
                    char_part = " "  # 0x00 = space per PCS spec
                else:
                    continue  # skip malformed entries

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

    # Fullwidth → halfwidth mapping for characters the LLM likes to produce
    _FULLWIDTH_MAP = str.maketrans(
        "０１２３４５６７８９"
        "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
        "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
        "（）～",
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "()~",
    )

    # Characters to replace with charmap-safe alternatives
    _CHAR_REPLACEMENTS = {
        "\u2014": "-",    # em dash → hyphen
        "\u2013": "-",    # en dash → hyphen
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201C": "\"",   # left double quote (will be skipped if not in charmap)
        "\u201D": "\"",   # right double quote
        "\u300A": "\"",   # 《 → "
        "\u300B": "\"",   # 》 → "
        "\u3001": ",",    # 、 → ,
        "\uFF5E": "~",    # ～ fullwidth tilde
        "\u00B7": ".",    # middle dot
        "$": "",          # dollar sign (not in charmap, strip)
    }

    def _sanitize(self, text: str) -> str:
        """Normalize characters that aren't in the charmap to safe alternatives."""
        # Apply language-specific character replacements first
        text = postprocess_for_language(text, self.target_lang)

        # Fullwidth → halfwidth
        text = text.translate(self._FULLWIDTH_MAP)
        # Character replacements
        for old, new in self._CHAR_REPLACEMENTS.items():
            if old in text:
                text = text.replace(old, new)
        # Strip any remaining stray curly braces (not part of {XX} hex patterns)
        import re
        text = re.sub(r"\{(?![0-9A-Fa-f]{2}\})", "", text)
        text = re.sub(r"(?<!\{[0-9A-Fa-f]{2})\}", "", text)
        return text

    def encode(self, text: str) -> bytes:
        """Encode text to ROM bytes using pcs_codes for control codes + charmap for chars.

        This is a convenience alias that delegates to encode_string but also
        handles backslash codes and bracket macros from pcs_codes.
        """
        from .pcs_codes import BACKSLASH_CODES, BRACKET_MACROS

        # Pre-clean: strip stray curly braces around control codes from LLM output
        import re
        text = re.sub(r"\{(\\[pnlr.]|\n\n?)\}", r"\1", text)
        # Also strip {\\?XX}, {\\CCXXXX} etc.
        text = re.sub(r"\{(\\(?:\?[0-9A-Fa-f]{2}|CC[0-9A-Fa-f]{4}|btn[0-9A-Fa-f]{2}|B[0-9A-Fa-f]))\}", r"\1", text)

        # Sanitize unsupported characters
        text = self._sanitize(text)

        result = bytearray()
        i = 0
        while i < len(text):
            # Handle real newline characters (0x0A) from JSON
            if text[i] == "\n":
                if i + 1 < len(text) and text[i + 1] == "\n":
                    # \n\n = paragraph wait (0xFB)
                    result.append(0xFB)
                    i += 2
                else:
                    # single \n = newline (0xFE)
                    result.append(0xFE)
                    i += 1
                continue

            # Skip carriage returns
            if text[i] == "\r":
                i += 1
                continue

            # Try bracket macros: [player], [rival], [red], etc.
            if text[i] == "[":
                end = text.find("]", i)
                if end != -1:
                    token = text[i : end + 1]
                    if token in BRACKET_MACROS:
                        result.extend(BRACKET_MACROS[token])
                        i = end + 1
                        continue

            # Try backslash codes (longest first)
            matched = False
            if text[i] == "\\":
                for code_str, code_bytes in BACKSLASH_CODES:
                    if text[i:].startswith(code_str):
                        result.extend(code_bytes)
                        i += len(code_str)
                        matched = True
                        break
                # \\CC hex codes: \CCXXYY... -> FC XX YY ...
                if not matched and text[i:].startswith("\\CC"):
                    j = i + 3
                    hex_chars = []
                    while j < len(text) and j - (i + 3) < 20:
                        pair = text[j : j + 2]
                        if len(pair) == 2 and all(c in "0123456789ABCDEFabcdef" for c in pair):
                            hex_chars.append(int(pair, 16))
                            j += 2
                        else:
                            break
                    if hex_chars:
                        result.append(0xFC)
                        result.extend(hex_chars)
                        i = j
                        matched = True
                # \\btn hex codes: \btnXX -> F8 XX
                if not matched and text[i:].startswith("\\btn"):
                    pair = text[i + 4 : i + 6]
                    if len(pair) == 2 and all(c in "0123456789ABCDEFabcdef" for c in pair):
                        result.append(0xF8)
                        result.append(int(pair, 16))
                        i += 6
                        matched = True
            if matched:
                continue

            # Try raw byte placeholder {XX}
            if text[i] == "{" and i + 3 < len(text) and text[i + 3] == "}":
                hex_str = text[i + 1 : i + 3]
                if all(c in "0123456789ABCDEFabcdef" for c in hex_str):
                    result.append(int(hex_str, 16))
                    i += 4
                    continue

            # Regular character via charmap
            enc = self.encode_char(text[i])
            if enc is not None:
                result.extend(enc)
            else:
                # Skip unsupported characters instead of crashing
                # (rare kanji, stray symbols, etc.)
                pass
            i += 1

        result.append(0xFF)  # PCS terminator
        return bytes(result)


def get_default_charmap() -> Charmap:
    """Return a Charmap instance with the default font patch charmap."""
    return Charmap()
