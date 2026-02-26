# Critical Bug Fix: Translation Detection for Latin Languages

## Issue
The `_translation_unchanged()` method in `translator.py` was checking if text was translated by looking for Chinese characters. For Latin-to-Latin translations (English→Spanish, English→French, etc.), this check always failed because Spanish/French/German text is also mostly ASCII letters.

**Symptom:** All batches showed "[部分未翻译，不缓存此批次]" (Partially untranslated, not caching this batch) even though translations were working.

## Root Cause
Lines 250-255 in the original code:
```python
# Check if the translated text still has mostly ASCII letters
# (meaning it wasn't really translated to Chinese)
ascii_letters = sum(1 for c in translated if c.isascii() and c.isalpha())
chinese_chars = sum(1 for c in translated if "\u4e00" <= c <= "\u9fff")
total = ascii_letters + chinese_chars
if total > 0 and ascii_letters / total > 0.8:
    return True  # Considered "untranslated"
```

This logic assumes that a "real" translation should have Chinese characters. For Spanish→"Hola mundo", this would be 100% ASCII letters and marked as "untranslated".

## Fix
Made `_translation_unchanged()` language-aware:

```python
def _translation_unchanged(self, original: str, translated: str) -> bool:
    """Check if the API returned text essentially unchanged (not translated)."""
    orig_norm = original.strip().lower()
    trans_norm = translated.strip().lower()

    if orig_norm == trans_norm:
        return True

    # For CJK target languages, check if translation actually contains CJK characters
    from .languages import is_cjk_language
    if is_cjk_language(self.target_lang):
        # Check if the translated text still has mostly ASCII letters
        # (meaning it wasn't really translated to Chinese/Japanese/Korean)
        ascii_letters = sum(1 for c in translated if c.isascii() and c.isalpha())
        chinese_chars = sum(1 for c in translated if "\u4e00" <= c <= "\u9fff")
        total = ascii_letters + chinese_chars
        if total > 0 and ascii_letters / total > 0.8:
            return True

    # For Latin-to-Latin translations, we can't use character set detection
    # Just check if the text is exactly the same
    return False
```

## Additional Fixes
Also fixed `_translate_individually()` which had hardcoded Chinese prompts:
- Now uses `self.prompts["system"]` instead of removed `SYSTEM_PROMPT`
- Uses language-appropriate user prompts for single-text fallback

## Testing
```bash
# Test translation detection
python -c "
from meowth.translator import Translator

t_es = Translator(source_lang='en', target_lang='es')
print(t_es._translation_unchanged('Hello', 'Hola'))  # False - different text
print(t_es._translation_unchanged('Hello', 'Hello'))  # True - same text
"
```

## Impact
- Latin-to-Latin translations now cache properly
- No more false "untranslated" warnings
- Chinese translation detection still works correctly
- Backward compatibility maintained

## Files Modified
- `src/meowth/translator.py` - Fixed `_translation_unchanged()` and `_translate_individually()`
