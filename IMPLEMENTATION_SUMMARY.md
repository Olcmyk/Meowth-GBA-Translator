# Latin-to-Latin Language Translation Support - Implementation Summary

## Overview

Successfully implemented support for Latin-to-Latin language translations (Spanish, German, French, Italian, Portuguese) in the Meowth GBA Pokemon translation tool. The system now supports translations between any of the 7 supported languages without requiring font patching for Latin languages.

## Supported Languages

- **English** (en) - PokeAPI ID: 9
- **Spanish** (es) - PokeAPI ID: 7
- **French** (fr) - PokeAPI ID: 5
- **German** (de) - PokeAPI ID: 6
- **Italian** (it) - PokeAPI ID: 8
- **Portuguese (Brazil)** (pt-BR) - PokeAPI ID: 1
- **Simplified Chinese** (zh-Hans) - PokeAPI ID: 12

## Key Changes

### 1. CLI Language Parameters (cli.py)
- Added `--source` and `--target` options to all commands (extract, translate, build, full)
- Default values: `--source en --target zh-Hans` (maintains backward compatibility)
- Language validation using `languages.validate_language()`

**Usage:**
```bash
# Spanish translation
meowth translate work/texts.json --source en --target es -o work/texts_es.json

# French translation
meowth build rom.gba --translations texts_fr.json --source en --target fr -o rom_fr.gba
```

### 2. Language Configuration (languages.py)
- Already existed with complete language definitions
- Contains `SUPPORTED_LANGUAGES` dict with PokeAPI IDs
- Provides `is_cjk_language()` and `is_latin_language()` helpers
- Includes `LATIN_CHAR_REPLACEMENTS` for Portuguese (ã→a, õ→o)
- `postprocess_for_language()` applies character replacements

### 3. Conditional Font Patching (pipeline.py)
- Font patch now only applied for CJK languages (line 322-330)
- Latin languages skip font patch entirely
- Prints appropriate message: "Skipping font patch for Latin language (es)"
- Uses `is_cjk_language(self.target_lang)` check

**Before:**
```python
# Always applied font patch
print("  Applying font patch...")
apply_font_patch(temp_rom, temp_rom, game=self.game)
```

**After:**
```python
if is_cjk_language(self.target_lang):
    print("  Applying font patch...")
    apply_font_patch(temp_rom, temp_rom, game=self.game)
else:
    print(f"  Skipping font patch for Latin language ({self.target_lang})")
```

### 4. Generalized Glossary (glossary.py)
- Accepts `source_lang` and `target_lang` parameters
- Maps language codes to PokeAPI IDs dynamically
- Builds source→target mappings for any language pair
- JSON cache filenames include language pair: `glossary_en_es.json`
- Renamed `en_to_zh` to `source_to_target` throughout

**Key methods updated:**
- `__init__(source_lang="en", target_lang="zh-Hans")`
- `_load_csv()` - builds dynamic mappings using PokeAPI IDs
- `lookup()` - renamed parameter from `english` to `source_text`
- `apply_to_text()` - works with any language pair
- `get_context_terms()` - returns source→target pairs

### 5. Generalized Translator (translator.py)
- Created `PROMPT_TEMPLATES` dict with language-specific prompts
- Chinese template preserved exactly (proven to work well)
- Generic template for other languages with {source_lang}/{target_lang} placeholders
- Accepts `source_lang` and `target_lang` parameters
- Selects appropriate prompt template in `__init__()`

**Template structure:**
```python
PROMPT_TEMPLATES = {
    "zh-Hans": {
        "system": "你是一个专业的宝可梦游戏本地化翻译专家...",
        "user": "请将以下宝可梦游戏文本从英文翻译成简体中文..."
    },
    "generic": {
        "system": "You are a professional Pokemon game localization expert. Translate from {source_lang} to {target_lang}...",
        "user": "Translate the following Pokemon game text from {source_lang} to {target_lang}..."
    }
}
```

### 6. Language-Aware Character Filtering (charmap.py)
- Added `target_lang` parameter to `__init__()`
- Calls `postprocess_for_language()` in `_sanitize()` method
- Applies language-specific character replacements during encoding
- Portuguese ã/õ replaced with a/o before encoding

**Character replacement flow:**
1. `postprocess_for_language()` - language-specific replacements
2. Fullwidth → halfwidth conversion
3. Generic character replacements (em dash, quotes, etc.)
4. Strip stray curly braces

### 7. Updated RomWriter (rom_writer.py)
- Added `target_lang` parameter to `__init__()`
- Passes `target_lang` to Charmap constructor
- Removed unused `get_default_charmap()` import

### 8. Latin-Optimized Text Wrapping (text_wrap.py)
- Added `target_lang` parameter to `wrap_text()`
- For Latin languages: simplified wrapping (text is more compact)
- For CJK languages: aggressive wrapping with character width calculations
- Latin text preserves structure without aggressive line breaking

**Latin wrapping logic:**
```python
if not is_cjk_language(target_lang):
    # Just normalize line breaks and preserve structure
    text = text.replace("\\.", "\\p")
    text = text.replace("\n\n", "\\p")
    return text
```

### 9. Pipeline Integration (pipeline.py)
- Added `source_lang` and `target_lang` parameters to `__init__()`
- Default values: `source_lang="en"`, `target_lang="zh-Hans"`
- Passes language parameters to all components:
  - `Charmap(target_lang=target_lang)`
  - `Glossary(source_lang=source_lang, target_lang=target_lang)`
  - `Translator(source_lang=source_lang, target_lang=target_lang)`
  - `RomWriter(..., target_lang=target_lang)`
  - `wrap_text(..., target_lang=target_lang)`

## Backward Compatibility

All changes maintain 100% backward compatibility:
- Default parameters match original behavior (EN→ZH)
- Existing code without language parameters works unchanged
- Chinese translation pipeline unchanged
- Font patch still applied for CJK languages

**Test results:**
```bash
✓ Default pipeline (backward compatibility) created
✓ EN→ZH glossary created
✓ EN→ZH translator created
✓ Chinese is CJK
```

## Testing

### Automated Tests (test_languages.sh)
All 8 automated test categories passed:
1. ✓ CLI language parameters exist
2. ✓ Language validation works for all 7 languages
3. ✓ CJK detection works correctly
4. ✓ Glossary initialization for different language pairs
5. ✓ Translator initialization for different languages
6. ✓ Charmap with target language parameter
7. ✓ Pipeline initialization with language parameters
8. ✓ Portuguese character replacements

### Manual Testing Steps

**1. Backward Compatibility (Chinese):**
```bash
meowth extract testgba/emerald_en.gba -o work/texts.json
meowth translate work/texts.json -o work/texts_translated.json
meowth build testgba/emerald_en.gba --translations work/texts_translated.json -o outputs/emerald_cn.gba
```
Expected: Font patch applied, Chinese text displays correctly

**2. Latin-to-Latin Translation (Spanish):**
```bash
meowth extract testgba/firered_en.gba -o work/texts.json --source en --target es
meowth translate work/texts.json --source en --target es -o work/texts_es.json
meowth build testgba/firered_en.gba --translations work/texts_es.json --source en --target es -o outputs/firered_es.gba
```
Expected: Font patch skipped, Spanish text displays correctly

**3. Emulator Verification:**
- Font patch should be skipped for Latin languages (check console output)
- Text should display correctly without font corruption
- Accented characters should render properly (á, é, í, ó, ú, ñ, ü, etc.)
- Control codes (\\p, \\n) should work properly
- Terminology should use official translations from PokeAPI

## Files Modified

1. `src/meowth/cli.py` - Added language parameters to all commands
2. `src/meowth/pipeline.py` - Language parameters, conditional font patch
3. `src/meowth/glossary.py` - Generalized for any language pair
4. `src/meowth/translator.py` - Language-specific prompt templates
5. `src/meowth/charmap.py` - Language-aware character filtering
6. `src/meowth/rom_writer.py` - Target language parameter
7. `src/meowth/text_wrap.py` - Latin-optimized wrapping
8. `src/meowth/languages.py` - Already existed, no changes needed

## Files Created

1. `test_languages.sh` - Automated test script

## Architecture Decisions

### 1. Encoding Strategy
- **Latin languages:** Use PCS (Pokemon Character Set) single-byte encoding
- **CJK languages:** Use font patch charmap with multi-byte encoding
- Decision based on: GBA's built-in PCS already supports most Latin characters

### 2. Character Filtering
- Applied during encoding, not translation
- Preserves LLM output quality
- Language-specific replacements only for truly unsupported characters

### 3. Backward Compatibility
- All new parameters have defaults matching current EN→ZH behavior
- No breaking changes to existing code
- Existing workflows continue to work unchanged

### 4. Language Detection
- Based on target language parameter, not ROM detection
- Explicit user control over translation direction
- Supports any source→target combination

### 5. Terminology
- Use PokeAPI databases for all language pairs
- All 5 Latin languages have complete terminology available
- Dynamic glossary loading based on language pair

## Known Limitations

1. **Portuguese (pt-BR):** Characters ã and õ are replaced with a and o (not in PCS charset)
2. **Font Patch:** Only supports CJK languages (Chinese, Japanese, Korean)
3. **PokeAPI Data:** Requires PokeAPI CSV files in `pokeapi-master/data/v2/csv/`
4. **LLM Translation:** Requires DeepSeek API key for translation step

## Future Enhancements

1. Add support for Traditional Chinese (zh-Hant)
2. Add support for Japanese (ja) and Korean (ko)
3. Pre-build glossary JSON files for common language pairs
4. Add language-specific text length validation
5. Support for custom terminology glossaries
6. Batch translation optimization for Latin languages

## Conclusion

The implementation successfully extends Meowth to support Latin-to-Latin translations while maintaining full backward compatibility with the existing Chinese translation pipeline. All automated tests pass, and the system is ready for manual testing with actual ROM files.

The key innovation is conditional font patching based on target language, which allows Latin languages to use the GBA's built-in PCS encoding without requiring custom font patches. This significantly simplifies the translation pipeline for Latin languages while preserving the sophisticated font patching system for CJK languages.
