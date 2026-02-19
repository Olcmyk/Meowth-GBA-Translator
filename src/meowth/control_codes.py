"""PCS control code protection for translation."""

from .pcs_codes import CONTROL_CODE_REGEX


def protect(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace control codes with numbered placeholders.

    Handles both HMA backslash codes and actual newline chars.
    HMA exports: \\n\\n = paragraph wait, single \\n = newline.

    Returns (protected_text, [(placeholder, original), ...])
    """
    codes: list[tuple[str, str]] = []

    def make_placeholder(original: str) -> str:
        idx = len(codes)
        placeholder = f"{{C{idx}}}"
        codes.append((placeholder, original))
        return placeholder

    # First pass: protect actual newlines (from HMA JSON export)
    # \n\n = paragraph wait, single \n = newline
    # Must do this BEFORE regex pass since regex won't match actual newlines
    parts = []
    i = 0
    while i < len(text):
        if text[i] == "\n" and i + 1 < len(text) and text[i + 1] == "\n":
            parts.append(make_placeholder("\n\n"))
            i += 2
        elif text[i] == "\n":
            parts.append(make_placeholder("\n"))
            i += 1
        else:
            parts.append(text[i])
            i += 1
    text = "".join(parts)

    # Second pass: protect HMA backslash control codes via regex
    def replacer(m):
        return make_placeholder(m.group(0))

    protected = CONTROL_CODE_REGEX.sub(replacer, text)
    return protected, codes


def restore(text: str, codes: list[tuple[str, str]]) -> str:
    """Restore control code placeholders to original codes."""
    for placeholder, original in codes:
        text = text.replace(placeholder, original)
    return text
