"""Language configuration — single source of truth for supported languages."""

SUPPORTED_LANGUAGES: dict[str, dict] = {
    "en":      {"name": "English",              "pokeapi_id": 9},
    "es":      {"name": "Spanish",              "pokeapi_id": 7},
    "fr":      {"name": "French",               "pokeapi_id": 5},
    "de":      {"name": "German",               "pokeapi_id": 6},
    "it":      {"name": "Italian",              "pokeapi_id": 8},
    "pt-BR":   {"name": "Portuguese (Brazil)",  "pokeapi_id": 1},
    "zh-Hans": {"name": "Simplified Chinese",   "pokeapi_id": 12},
}

_CJK_LANGUAGES = {"zh-Hans", "zh-Hant", "ja", "ko"}
_LATIN_LANGUAGES = {"en", "es", "fr", "de", "it", "pt-BR"}

# Characters that exist in some Latin languages but not in GBA PCS charset
LATIN_CHAR_REPLACEMENTS: dict[str, dict[str, str]] = {
    "pt-BR": {"ã": "a", "Ã": "A", "õ": "o", "Õ": "O"},
}


def is_cjk_language(lang: str) -> bool:
    """Return True if the language uses CJK characters (needs font patch)."""
    return lang in _CJK_LANGUAGES


def is_latin_language(lang: str) -> bool:
    """Return True if the language uses Latin script (no font patch needed)."""
    return lang in _LATIN_LANGUAGES


def get_language_name(lang: str) -> str:
    """Return the display name for a language code."""
    info = SUPPORTED_LANGUAGES.get(lang)
    return info["name"] if info else lang


def validate_language(lang: str) -> None:
    """Raise ValueError if the language code is not supported."""
    if lang not in SUPPORTED_LANGUAGES:
        supported = ", ".join(SUPPORTED_LANGUAGES.keys())
        raise ValueError(f"Unsupported language '{lang}'. Supported: {supported}")


def postprocess_for_language(text: str, target_lang: str) -> str:
    """Apply language-specific character replacements to translated text."""
    replacements = LATIN_CHAR_REPLACEMENTS.get(target_lang)
    if not replacements:
        return text
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
