"""Language configuration — single source of truth for supported languages."""

SUPPORTED_LANGUAGES: dict[str, dict] = {
    "en":      {"name": "English",              "name_zh": "英文",     "pokeapi_id": 9},
    "es":      {"name": "Spanish",              "name_zh": "西班牙文", "pokeapi_id": 7},
    "fr":      {"name": "French",               "name_zh": "法文",     "pokeapi_id": 5},
    "de":      {"name": "German",               "name_zh": "德文",     "pokeapi_id": 6},
    "it":      {"name": "Italian",              "name_zh": "意大利文", "pokeapi_id": 8},
    "zh-Hans": {"name": "Simplified Chinese",   "name_zh": "简体中文", "pokeapi_id": 12},
}

_CJK_LANGUAGES = {"zh-Hans", "zh-Hant", "ja", "ko"}
_LATIN_LANGUAGES = {"en", "es", "fr", "de", "it"}

# Characters that exist in some Latin languages but not in GBA PCS charset
LATIN_CHAR_REPLACEMENTS: dict[str, dict[str, str]] = {}


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


def get_language_name_zh(lang: str) -> str:
    """Return the Chinese display name for a language code."""
    info = SUPPORTED_LANGUAGES.get(lang)
    return info["name_zh"] if info else lang


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
