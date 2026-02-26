"""Language configuration — single source of truth for supported languages."""

SUPPORTED_LANGUAGES: dict[str, dict] = {
    "en":      {"name": "English",             "pokeapi_id": 9},
    "es":      {"name": "Spanish",             "pokeapi_id": 7},
    "fr":      {"name": "French",              "pokeapi_id": 5},
    "de":      {"name": "German",              "pokeapi_id": 6},
    "it":      {"name": "Italian",             "pokeapi_id": 8},
    "zh-Hans": {"name": "Simplified Chinese",  "pokeapi_id": 12},
}

# Languages that use CJK characters and require a font patch
_CJK_LANGUAGES = {"zh-Hans", "zh-Hant", "ja", "ko"}

# Languages that use the Latin alphabet (PCS native charset is sufficient)
_LATIN_LANGUAGES = {"en", "es", "fr", "de", "it"}


def is_cjk_language(lang: str) -> bool:
    """Return True if the language requires CJK font patch."""
    return lang in _CJK_LANGUAGES


def is_latin_language(lang: str) -> bool:
    """Return True if the language uses only Latin/PCS-native characters."""
    return lang in _LATIN_LANGUAGES


def get_language_name(lang: str) -> str:
    """Return the English display name for a language code."""
    info = SUPPORTED_LANGUAGES.get(lang)
    if info is None:
        raise ValueError(f"Unsupported language: {lang}")
    return info["name"]


def get_pokeapi_id(lang: str) -> int:
    """Return the PokeAPI local_language_id for a language code."""
    info = SUPPORTED_LANGUAGES.get(lang)
    if info is None:
        raise ValueError(f"Unsupported language: {lang}")
    return info["pokeapi_id"]


def validate_language_pair(source: str, target: str) -> None:
    """Validate that source and target form a supported translation pair.

    Supported pairs:
    - Any European language (en/de/fr/it/es) ↔ any other European language
    - Any European language → zh-Hans
    """
    if source == target:
        raise ValueError(f"Source and target language are the same: {source}")
    if source not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported source language: {source}")
    if target not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported target language: {target}")
    if is_cjk_language(source):
        raise ValueError(f"CJK source language not supported: {source}")
