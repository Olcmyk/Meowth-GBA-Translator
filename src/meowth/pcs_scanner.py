"""PCS text filter utilities.

MeowthBridge (C#) handles all text extraction via HMA PCSRun + loadpointer.
This module only provides filtering/analysis helpers used by other stages.
"""

import re


def is_real_text(text: str) -> bool:
    """Check if text looks like real human-readable text (not binary garbage).

    Used by rom_writer to skip entries that passed PCS validation but
    aren't meaningful text.
    """
    if not text or len(text) < 2:
        return False
    # Strip control code representations before checking — their hex digits
    # inflate the ASCII-letter ratio and let garbage slip through.
    clean = re.sub(r'\\CC[0-9A-Fa-f]+', '', text)
    clean = re.sub(r'\\btn[0-9A-Fa-f]{2}', '', clean)
    clean = re.sub(r'\\\?[0-9A-Fa-f]{2}', '', clean)
    clean = re.sub(r'\\[0-9A-Fa-f]{2}', '', clean)
    clean = re.sub(r'\\[pnlre.+<>]', '', clean)
    clean = re.sub(r'\\(pk|mn|Po|Ke|Bl|Lo|Ck|Lv|qo|qc|sm|sf|au|ad|al|ar|pn)', '', clean)
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\\![0-9A-Fa-f]+', '', clean)
    if not clean or len(clean) < 2:
        return False
    # Must have at least one ASCII letter (not just accented chars like î ê)
    if not any(c.isascii() and c.isalpha() for c in clean):
        return False
    # Must have reasonable ASCII letter ratio
    ascii_letters = sum(1 for c in clean if c.isascii() and c.isalpha())
    if len(clean) > 0 and ascii_letters / len(clean) < 0.3:
        return False
    return True


def is_fragment(text: str) -> bool:
    """Check if text looks like a fragment (pointing to middle of another string)."""
    if not text:
        return True
    clean = text.strip('"')
    if not clean:
        return True
    first = clean[0]
    if first.islower() or first == ' ':
        return True
    if first in ('.', ',', ';', ':', ')', ']', '}', "'"):
        return True
    return False


def filter_entries(entries: list) -> list:
    """Filter entries to keep only real text."""
    result = []
    for entry in entries:
        category = entry.get('category', '')
        if category != 'scripts':
            result.append(entry)
            continue
        original = entry.get('original', '')
        if not is_real_text(original):
            continue
        entry_id = entry.get('id', '')
        if entry_id.startswith('ptr_') and is_fragment(original):
            continue
        result.append(entry)
    return result


def analyze_entries(entries: list) -> dict:
    """Analyze entries and return statistics."""
    stats = {
        'total': len(entries),
        'by_category': {},
        'scripts_real': 0,
        'scripts_filtered': 0,
    }
    for entry in entries:
        cat = entry.get('category', 'unknown')
        stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
        if cat == 'scripts':
            if is_real_text(entry.get('original', '')):
                stats['scripts_real'] += 1
            else:
                stats['scripts_filtered'] += 1
    return stats
