"""PCS (Pokemon Character Set) text decoder for Gen3 games.

This module replicates the ValidatePcsText and text conversion logic
from TextExtractor.cs, ensuring byte-perfect compatibility.
"""

from typing import Tuple


class PcsDecoder:
    """Decodes Gen3 Pokemon PCS text format.

    Replicates HMA's TextConverter.Convert() and ValidatePcsText() logic
    from TextExtractor.cs lines 218-292.
    """

    # PCS character mapping (Gen3 standard charset)
    # Based on HMA's PCS table and resources/pcsReference.txt
    PCS_CHARS = {
        0x00: " ",  # Space
        # Extended characters 0x01-0x50
        0x2C: "\\e", 0x2D: "&", 0x2E: "\\+",
        0x34: "\\Lv",
        0x48: "\\r",
        # Extended characters 0x51-0xA0
        0x51: "¿", 0x52: "¡",
        0x53: "\\pk", 0x54: "\\mn",
        0x55: "\\Po", 0x56: "\\Ke", 0x57: "\\Bl", 0x58: "\\Lo", 0x59: "\\Ck",
        0x68: "â", 0x6F: "í",
        0x79: "\\au", 0x7A: "\\ad", 0x7B: "\\al", 0x7C: "\\ar",
        0x84: "\\d", 0x85: "\\<", 0x86: "\\>",
        # Digits 0xA1-0xAA
        0xA1: "0", 0xA2: "1", 0xA3: "2", 0xA4: "3", 0xA5: "4",
        0xA6: "5", 0xA7: "6", 0xA8: "7", 0xA9: "8", 0xAA: "9",
        # Punctuation 0xAB-0xBA
        0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-", 0xAF: "·",
        0xB0: "\\.", 0xB1: "\\qo", 0xB2: "\\qc", 0xB3: "'", 0xB4: "'",
        0xB5: "\\sm", 0xB6: "\\sf", 0xB7: "$", 0xB8: ",", 0xB9: "×",
        0xBA: ":",
        # 0xBB-0xD4: A-Z
        0xBB: "A", 0xBC: "B", 0xBD: "C", 0xBE: "D", 0xBF: "E",
        0xC0: "F", 0xC1: "G", 0xC2: "H", 0xC3: "I", 0xC4: "J",
        0xC5: "K", 0xC6: "L", 0xC7: "M", 0xC8: "N", 0xC9: "O",
        0xCA: "P", 0xCB: "Q", 0xCC: "R", 0xCD: "S", 0xCE: "T",
        0xCF: "U", 0xD0: "V", 0xD1: "W", 0xD2: "X", 0xD3: "Y",
        0xD4: "Z",
        # 0xD5-0xEE: a-z
        0xD5: "a", 0xD6: "b", 0xD7: "c", 0xD8: "d", 0xD9: "e",
        0xDA: "f", 0xDB: "g", 0xDC: "h", 0xDD: "i", 0xDE: "j",
        0xDF: "k", 0xE0: "l", 0xE1: "m", 0xE2: "n", 0xE3: "o",
        0xE4: "p", 0xE5: "q", 0xE6: "r", 0xE7: "s", 0xE8: "t",
        0xE9: "u", 0xEA: "v", 0xEB: "w", 0xEC: "x", 0xED: "y",
        0xEE: "z",
        # Special characters
        0x1B: "é",  # Accented e
        0xEF: "\\sm",  # Male symbol
        0xF0: "\\sf",  # Female symbol
        # 0xF1-0xF9: Special characters/control codes (handled separately)
        0xFA: "\n",  # Line feed (converted to newline by HMA)
        0xFB: "\n",  # Paragraph feed (converted to newline by HMA)
        # 0xFC, 0xFD, 0xFE, 0xF7, 0xF8, 0xF9: Control codes (handled separately)
        0xFF: "",  # Terminator (not printed)
    }

    def __init__(self, rom_data: bytearray):
        """Initialize PCS decoder with ROM data.

        Args:
            rom_data: GBA ROM byte array
        """
        self.rom_data = rom_data

    def validate_pcs_text(self, address: int) -> int:
        """Validate if address contains valid PCS text.

        Replicates ValidatePcsText() from TextExtractor.cs lines 226-292.
        Returns text length (including 0xFF terminator) if valid, 0 otherwise.

        Validation criteria:
        - Must end with 0xFF terminator within MAX_LENGTH
        - Must have ≥2 letters (A-Z, a-z, é)
        - Must have ≥20% letter ratio (letters / total_printable)

        Args:
            address: ROM offset to validate

        Returns:
            Text length including terminator, or 0 if invalid
        """
        if address < 0 or address >= len(self.rom_data):
            return 0

        MAX_LENGTH = 2000
        letters = 0
        total_printable = 0

        for i in range(MAX_LENGTH):
            if address + i >= len(self.rom_data):
                return 0

            b = self.rom_data[address + i]

            # Terminator found
            if b == 0xFF:
                if letters < 2:
                    return 0
                # Letter ratio check: filter binary data masquerading as text
                if total_printable > 0 and letters / total_printable < 0.20:
                    return 0
                return i + 1

            # A-Z (0xBB-0xD4), a-z (0xD5-0xEE), é (0x1B) — count as letters
            if (0xBB <= b <= 0xD4) or (0xD5 <= b <= 0xEE) or b == 0x1B:
                letters += 1
                total_printable += 1
                continue

            # Space (0x00), digits (0xA1-0xAA), punctuation (0xAB-0xBA including colon)
            if b == 0x00 or (0xA1 <= b <= 0xBA):
                total_printable += 1
                continue

            # Newline/paragraph control codes
            if b in (0xFA, 0xFB, 0xFE):
                total_printable += 1
                continue

            # Control codes with parameters: FC, FD — skip parameter byte
            if b == 0xFC and address + i + 1 < len(self.rom_data):
                i += 1
                continue
            if b == 0xFD and address + i + 1 < len(self.rom_data):
                i += 1
                continue

            # Extended PCS characters: 0x01-0x50, 0x51-0xA0, 0xEF-0xF9
            if (0x01 <= b <= 0x50) or (0x51 <= b <= 0xA0) or (0xEF <= b <= 0xF9):
                total_printable += 1
                continue

            # Not in any valid PCS range — not text
            return 0

        # No terminator found within MAX_LENGTH
        return 0

    def decode_pcs_text(self, address: int, length: int) -> str:
        """Decode PCS text at address.

        Replicates HMA's TextConverter.Convert() behavior.
        Wraps output in quotes like HMA does.

        Args:
            address: ROM offset of text
            length: Text length including terminator

        Returns:
            Decoded text string wrapped in quotes
        """
        if address < 0 or address + length > len(self.rom_data):
            return '""'

        result = []
        i = 0
        newline_count = 0  # Track newline count for HMA quirk

        while i < length:
            b = self.rom_data[address + i]

            # Terminator
            if b == 0xFF:
                break

            # Control code 0xF7: \? with 1-byte parameter (displayed as 2-digit hex)
            if b == 0xF7:
                if i + 1 < length:
                    # Read 1-byte parameter (HMA displays as 2-digit hex like "00")
                    param = self.rom_data[address + i + 1]
                    result.append(f"\\?{param:02X}")
                    i += 2
                    continue
                else:
                    result.append("\\?")
                    i += 1
                    continue

            # Control code 0xF8: \btn with 1-byte parameter
            if b == 0xF8:
                if i + 1 < length:
                    param = self.rom_data[address + i + 1]
                    result.append(f"\\btn{param:02X}")
                    i += 2
                    continue
                else:
                    result.append("\\btn")
                    i += 1
                    continue

            # Control code 0xF9: \9 with possible parameter
            if b == 0xF9:
                if i + 1 < length:
                    param = self.rom_data[address + i + 1]
                    result.append(f"\\9{param:02X}")
                    i += 2
                    continue
                else:
                    result.append("\\9")
                    i += 1
                    continue

            # Newline: 0xFE
            # HMA quirk: first newline is real \n, all subsequent ones are literal "\\n" + real \n
            if b == 0xFE:
                newline_count += 1
                if newline_count == 1:
                    # First: real newline
                    result.append("\n")
                else:
                    # Subsequent: literal \n followed by real newline
                    result.append("\\n\n")
                i += 1
                continue

            # Control code with parameter: FC
            if b == 0xFC:
                if i + 1 < length:
                    param = self.rom_data[address + i + 1]
                    result.append(f"\\\\{param:02X}")
                    i += 2
                    continue
                else:
                    i += 1
                    continue

            # Control code with parameter: FD (escape sequences)
            if b == 0xFD:
                if i + 1 < length:
                    param = self.rom_data[address + i + 1]
                    # HMA uses specific escape sequences for known FD codes
                    if param == 0x01:
                        result.append("[player]")
                    elif param == 0x02:
                        result.append("[buffer1]")
                    elif param == 0x03:
                        result.append("[buffer2]")
                    elif param == 0x04:
                        result.append("[buffer3]")
                    elif param == 0x06:
                        result.append("[rival]")
                    else:
                        # Unknown FD codes: output as raw escape
                        result.append(f"\\\\{param:02X}")
                    i += 2
                    continue
                else:
                    i += 1
                    continue

            # Regular PCS character
            if b in self.PCS_CHARS:
                result.append(self.PCS_CHARS[b])
            else:
                # Extended character not in our table — use placeholder
                result.append(f"[{b:02X}]")

            i += 1

        # Wrap in quotes like HMA does
        return '"' + ''.join(result) + '"'
