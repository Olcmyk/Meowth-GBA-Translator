"""PCS control code protection for translation."""

import re

# PCS control codes from HMA's pcsReference.txt
# These must be preserved during translation
CONTROL_CODES = [
    # Multi-char codes (must match before single-char)
    (r"\\v\w{2}", "variable"),       # \vXX - variable references
    (r"\\pn", "pause_newline"),       # pause + newline
    (r"\\pk", "pk_symbol"),           # Poké symbol part
    (r"\\mn", "mn_symbol"),           # MON symbol part
    (r"\\Bl", "scroll"),              # scroll text
    (r"\\CC\w{2}", "color_code"),     # color codes
    (r"\[player\]", "player_name"),
    (r"\[rival\]", "rival_name"),
    # Single-char codes
    (r"\\n", "newline"),              # newline
    (r"\\l", "line_scroll"),          # line scroll
    (r"\\p", "paragraph"),            # paragraph break
    (r"\\e", "escape"),               # escape
]

# Combined pattern
_PATTERN = re.compile("|".join(f"({pat})" for pat, _ in CONTROL_CODES))


def protect(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace control codes with numbered placeholders.

    Returns (protected_text, [(placeholder, original), ...])
    """
    codes: list[tuple[str, str]] = []

    def replacer(m: re.Match) -> str:
        original = m.group(0)
        idx = len(codes)
        placeholder = f"{{C{idx}}}"
        codes.append((placeholder, original))
        return placeholder

    protected = _PATTERN.sub(replacer, text)
    return protected, codes


def restore(text: str, codes: list[tuple[str, str]]) -> str:
    """Restore control code placeholders to original codes."""
    for placeholder, original in codes:
        text = text.replace(placeholder, original)
    return text
