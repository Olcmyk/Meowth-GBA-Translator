"""Shared PCS control code definitions for GBA Pokemon text encoding.

Single source of truth for all control code mappings, derived from
HexManiacAdvance's pcsReference.txt. Used by:
- control_codes.py (regex protection for translation)
- rom_writer.py (text → ROM bytes encoding)
- pcs_scanner.py (ROM bytes → text decoding)
"""

# --- Byte → HMA text representation (for decoding ROM → text) ---

# PCS printable character table
PCS_CHAR_TABLE: dict[int, str] = {}

_CHAR_RANGES = [
    (0x00, " ÀÁÂÇÈÉÊËÌ"),
    (0x0B, "ÎÏÒÓÔ"),
    (0x10, "ŒÙÚÛÑßàá"),
    (0x19, "çèéêëì"),
    (0x20, "îïòóôœùúûñºª"),
    (0x5A, "Í%()"),
    (0xA1, "0123456789"),
    (0xAB, "!?.-‧"),
    (0xB7, "$,*/"),
    (0xBB, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    (0xD5, "abcdefghijklmnopqrstuvwxyz"),
    (0xF0, ":ÄÖÜäöü"),
]
for _start, _chars in _CHAR_RANGES:
    for _i, _ch in enumerate(_chars):
        PCS_CHAR_TABLE[_start + _i] = _ch

_CHAR_SINGLES = {
    0x2C: "\\e", 0x2D: "&", 0x2E: "\\+",
    0x34: "\\Lv", 0x35: "=", 0x36: ";",
    0x48: "\\r",
    0x51: "¿", 0x52: "¡",
    0x53: "\\pk", 0x54: "\\mn", 0x55: "\\Po",
    0x56: "\\Ke", 0x57: "\\Bl", 0x58: "\\Lo", 0x59: "\\Ck",
    0x68: "â", 0x6F: "í",
    0x79: "\\au", 0x7A: "\\ad", 0x7B: "\\al", 0x7C: "\\ar",
    0x84: "\\d", 0x85: "\\<", 0x86: "\\>",
    0xB0: "\\.", 0xB1: "\\qo", 0xB2: "\\qc",
    0xB3: "\u2018", 0xB4: "\u2019",
    0xB5: "\\sm", 0xB6: "\\sf",
}
PCS_CHAR_TABLE.update(_CHAR_SINGLES)

VALID_PCS_BYTES = frozenset(PCS_CHAR_TABLE.keys())

# --- Special byte constants ---

TERMINATOR = 0xFF
NEWLINE = 0xFE
LINE_SCROLL = 0xFA
PARAGRAPH = 0xFB
CONTROL_CODE_PREFIX = 0xFC
ESCAPE_PREFIX = 0xFD
F7_PREFIX = 0xF7
BUTTON_PREFIX = 0xF8
F9_PREFIX = 0xF9
F6_BYTE = 0xF6

# --- FC control code argument counts ---
# Most FC codes have 1 arg byte; codes > 0x14 have 0; exceptions listed here.
FC_ARG_COUNTS: dict[int, int] = {
    0x04: 3,  # text shadow highlight
    0x09: 0,  # pause
    0x0A: 0,  # wait for sound effect
    0x0B: 2,  # play background music
    0x10: 2,  # play sound effects
}


def fc_arg_count(cmd: int) -> int:
    """Return the number of argument bytes for an FC control code command."""
    if cmd in FC_ARG_COUNTS:
        return FC_ARG_COUNTS[cmd]
    return 0 if cmd > 0x14 else 1


# --- FD macros (escape + 1 byte) ---
FD_MACROS: dict[int, str] = {
    0x01: "[player]",
    0x02: "[buffer1]",
    0x03: "[buffer2]",
    0x04: "[buffer3]",
    0x05: "[kun]",
    0x06: "[rival]",
}

# --- F9 macros (F9 + 1 byte) ---
F9_MACROS: dict[int, str] = {
    0x00: "[up]", 0x01: "[down]", 0x02: "[left]", 0x03: "[right]",
    0x04: "[plus]", 0x05: "[LV]", 0x06: "[PP]", 0x07: "[ID]",
    0x08: "[No]", 0x09: "[_]",
    0x0A: "[1]", 0x0B: "[2]", 0x0C: "[3]", 0x0D: "[4]", 0x0E: "[5]",
    0x0F: "[6]", 0x10: "[7]", 0x11: "[8]", 0x12: "[9]",
    0x13: "[left_parenthesis]", 0x14: "[right_parenthesis]",
    0x15: "[super_effective]", 0x16: "[not_very_effective]",
    0x17: "[not_effective]",
    0xD0: "[down_bar]", 0xD1: "[vertical_bar]", 0xD2: "[up_bar]",
    0xD3: "[tilde]", 0xD4: "[left_parenthesis_bold]",
    0xD5: "[right_parenthesis_bold]", 0xD6: "[subset_of]",
    0xD7: "[greater_than_short]", 0xD8: "[left_eye]", 0xD9: "[right_eye]",
    0xDA: "[commercial_at]", 0xDB: "[semicolon]",
    0xDC: "[bold_plus_1]", 0xDD: "[bold_minus]", 0xDE: "[bold_equals]",
    0xDF: "[dazed]", 0xE0: "[tongue]", 0xE1: "[delta]",
    0xE2: "[acute]", 0xE3: "[grave]", 0xE4: "[circle]",
    0xE5: "[triangle]", 0xE6: "[square]", 0xE7: "[heart]",
    0xE8: "[moon]", 0xE9: "[eighth_note]", 0xEA: "[half_circle]",
    0xEB: "[thunderbolt]", 0xEC: "[leaf]", 0xED: "[fire]",
    0xEE: "[teardrop]", 0xEF: "[left_wing]", 0xF0: "[right_wing]",
    0xF1: "[rose]", 0xF2: "[unknown_F2]", 0xF3: "[unknown_F3]",
    0xF4: "[frustration_mark]", 0xF5: "[sad]", 0xF6: "[happy]",
    0xF7: "[angry]", 0xF8: "[excited]", 0xF9: "[joyful]",
    0xFA: "[maliciously_happy]", 0xFB: "[upset]", 0xFC: "[straight_face]",
    0xFD: "[surprised]", 0xFE: "[outraged]",
}

# --- FC macros (0-arg FC codes with bracket names) ---
FC_MACROS: dict[int, str] = {
    0x07: "[resetfont]",
    0x09: "[pause]",
    0x0A: "[wait_sound]",
    0x0C: "[escape]",
    0x0D: "[shift_right]",
    0x0E: "[shift_down]",
    0x0F: "[fill_window]",
    0x12: "[skip]",
    0x15: "[japanese]",
    0x16: "[latin]",
    0x17: "[pause_music]",
    0x18: "[resume_music]",
}

# --- Backslash code → byte mapping (for encoding text → ROM) ---
# Order: longer prefixes first to ensure correct matching.
BACKSLASH_CODES: list[tuple[str, bytes]] = [
    ("\\pn", bytes([PARAGRAPH])),
    ("\\pk", bytes([0x53])),
    ("\\mn", bytes([0x54])),
    ("\\Po", bytes([0x55])),
    ("\\Ke", bytes([0x56])),
    ("\\Bl", bytes([0x57])),
    ("\\Lo", bytes([0x58])),
    ("\\Ck", bytes([0x59])),
    ("\\Lv", bytes([0x34])),
    ("\\qo", bytes([0xB1])),
    ("\\qc", bytes([0xB2])),
    ("\\sm", bytes([0xB5])),
    ("\\sf", bytes([0xB6])),
    ("\\au", bytes([0x79])),
    ("\\ad", bytes([0x7A])),
    ("\\al", bytes([0x7B])),
    ("\\ar", bytes([0x7C])),
    ("\\n", bytes([NEWLINE])),
    ("\\l", bytes([LINE_SCROLL])),
    ("\\p", bytes([PARAGRAPH])),
    ("\\e", bytes([0x2C])),
    ("\\d", bytes([0x84])),
    ("\\.", bytes([0xB0])),
    ("\\<", bytes([0x85])),
    ("\\>", bytes([0x86])),
    ("\\+", bytes([0x2E])),
    ("\\r", bytes([0x48])),
]

# --- Bracket macro → byte mapping (for encoding text → ROM) ---
# Built from FD_MACROS, FC_MACROS, and F9_MACROS (reverse lookup).
BRACKET_MACROS: dict[str, bytes] = {}
for _val, _name in FD_MACROS.items():
    BRACKET_MACROS[_name] = bytes([ESCAPE_PREFIX, _val])
for _val, _name in FC_MACROS.items():
    BRACKET_MACROS[_name] = bytes([CONTROL_CODE_PREFIX, _val])
for _val, _name in F9_MACROS.items():
    BRACKET_MACROS[_name] = bytes([F9_PREFIX, _val])

# Color macros for FireRed (BPRE/BPGE)
_BPRE_COLORS: dict[str, int] = {
    "white": 0x00, "white2": 0x01, "black": 0x02, "grey": 0x03, "gray": 0x03,
    "red": 0x04, "orange": 0x05, "green": 0x06, "lightgreen": 0x07,
    "blue": 0x08, "lightblue": 0x09, "white3": 0x0A, "lightblue2": 0x0B,
    "cyan": 0x0C, "lightblue3": 0x0D, "navyblue": 0x0E, "darknavyblue": 0x0F,
}
for _name, _val in _BPRE_COLORS.items():
    BRACKET_MACROS[f"[{_name}]"] = bytes([CONTROL_CODE_PREFIX, 0x01, _val])


# --- Regex patterns for control code protection (used by control_codes.py) ---
import re

# Order matters: longer/more specific patterns first.
CONTROL_CODE_PATTERNS: list[tuple[str, str]] = [
    # Multi-byte codes with variable-length hex args
    (r"\\CC(?:[0-9A-Fa-f]{2})+", "control_code"),
    (r"\\btn[0-9A-Fa-f]{2}", "button"),
    (r"\\9[0-9A-Fa-f]{2}", "f9_code"),
    (r"\\F[0-9A-Fa-f]", "fx_code"),
    (r"\\\?[0-9A-Fa-f]{2}", "f7_code"),
    (r"\\v[0-9A-Fa-f]{2}", "variable"),
    (r"\\\\[0-9A-Fa-f]{2}", "fd_escape"),
]

# Add bracket macro patterns (sorted by length descending for greedy match)
_bracket_names = sorted(BRACKET_MACROS.keys(), key=len, reverse=True)
for _name in _bracket_names:
    _escaped = re.escape(_name)
    _label = _name.strip("[]").replace(" ", "_")
    CONTROL_CODE_PATTERNS.append((_escaped, _label))

# Add backslash code patterns (multi-char before single-char)
_seen_patterns: set[str] = set()
for _code_str, _ in BACKSLASH_CODES:
    _escaped = re.escape(_code_str)
    if _escaped not in _seen_patterns:
        _label = _code_str.lstrip("\\").replace(".", "ellipsis")
        CONTROL_CODE_PATTERNS.append((_escaped, _label))
        _seen_patterns.add(_escaped)

CONTROL_CODE_REGEX = re.compile(
    "|".join(f"({pat})" for pat, _ in CONTROL_CODE_PATTERNS)
)
