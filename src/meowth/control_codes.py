"""PCS control code protection for translation."""

import re

from .pcs_codes import CONTROL_CODE_REGEX

# GBA text box width in characters (English). Lines shorter than this
# threshold are considered semantic breaks, not layout wraps.
_GBA_LINE_WIDTH = 32
_SEMANTIC_THRESHOLD = int(_GBA_LINE_WIDTH * 0.75)  # 24 chars

# Pattern to strip control codes / escape sequences for visible-length calc
_INVISIBLE_RE = re.compile(
    r"\\btn[0-9A-Fa-f]{2}"
    r"|\\CC[0-9A-Fa-f]{4}"
    r"|\\B[0-9A-Fa-f]"
    r"|\\\?[0-9A-Fa-f]{2}"
    r"|\\[.plnr]"
    r"|\[[a-zA-Z_]\w*\]"
)


def _visible_length(line: str) -> int:
    """Return the visible character count of a line, ignoring control codes."""
    stripped = _INVISIBLE_RE.sub("", line)
    return len(stripped)


def _classify_newlines(text: str) -> str:
    """Replace newlines with semantic paragraph breaks or spaces.

    Rules:
    - \\n\\n → always a semantic paragraph break (keep as \\n\\n)
    - \\n where the preceding line is short (< 75% of GBA line width)
      → semantic break (keep as \\n\\n)
    - \\n where the preceding line is long (filled the text box)
      → layout wrap (replace with space)
    """
    _PARA = "\x00PARA\x00"
    text = text.replace("\n\n", _PARA)

    lines = text.split("\n")
    result_parts = []
    for i, line in enumerate(lines):
        result_parts.append(line)
        if i < len(lines) - 1:
            vis_len = _visible_length(line)
            if vis_len < _SEMANTIC_THRESHOLD:
                result_parts.append("\n\n")
            else:
                result_parts.append(" ")

    result = "".join(result_parts)
    result = result.replace(_PARA, "\n\n")
    return result


def protect(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace control codes with numbered placeholders.

    Handles both HMA backslash codes and actual newline chars.
    Intelligently classifies literal newlines:
    - \\n\\n = always semantic paragraph break
    - short line + \\n = semantic break (line didn't fill text box)
    - long line + \\n = layout wrap (join with space)

    Returns (protected_text, [(placeholder, original), ...])
    """
    codes: list[tuple[str, str]] = []

    def make_placeholder(original: str) -> str:
        idx = len(codes)
        placeholder = f"{{C{idx}}}"
        codes.append((placeholder, original))
        return placeholder

    # Pre-process: convert HMA break codes to semantic paragraph breaks
    # \p (page break) and \. (wait-for-button) are semantic break points
    # \l (scroll) and \n (newline) are pure layout — strip them
    result = text
    result = result.replace("\\.", "\n\n")
    result = result.replace("\\p", "\n\n")
    result = result.replace("\\l", "")
    result = result.replace("\\n", "")

    # Handle literal newlines (0x0A) from HMA extraction
    # Distinguish semantic paragraph breaks from layout line wraps
    result = result.replace("\r\n", "\n")
    result = _classify_newlines(result)

    # Now protect remaining \n\n as paragraph markers
    parts = []
    i = 0
    while i < len(result):
        if result[i] == "\n" and i + 1 < len(result) and result[i + 1] == "\n":
            parts.append(make_placeholder("\n\n"))
            i += 2
        elif result[i] == "\n":
            parts.append(make_placeholder("\n"))
            i += 1
        else:
            parts.append(result[i])
            i += 1
    result = "".join(parts)

    # Protect HMA backslash control codes via regex
    def replacer(m):
        return make_placeholder(m.group(0))

    protected = CONTROL_CODE_REGEX.sub(replacer, result)
    return protected, codes


def restore(text: str, codes: list[tuple[str, str]]) -> str:
    """Restore control code placeholders to original codes."""
    for placeholder, original in codes:
        text = text.replace(placeholder, original)
    return text
