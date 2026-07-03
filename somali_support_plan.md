# Adding Somali Translation Support to Meowth GBA Translator

To add support for the Somali language (`so`) to the Meowth GBA Translator project, changes will need to be made across several files to properly register the language, configure GUI forms, update localization mappings, and potentially handle character limitations.

Here is an analysis of the repository and the files that need to be updated.

## 1. Core Language Registration: `src/meowth/languages.py`

This is the main single source of truth for supported languages.

- Add `"so"` to the `SUPPORTED_LANGUAGES` dictionary:
  ```python
  "so":      {"name": "Somali",               "name_zh": "索马里文", "pokeapi_id": None}, # PokeAPI doesn't have Somali
  ```
- Since Somali uses the Latin script, add `"so"` to the `_LATIN_LANGUAGES` set:
  ```python
  _LATIN_LANGUAGES = {"en", "es", "fr", "de", "it", "so"}
  ```
- Consider adding any necessary character replacements to `LATIN_CHAR_REPLACEMENTS` if Somali uses specific characters (like specific quotes or apostrophes) that do not map cleanly to the default GBA Latin character set (PCS encoding).

## 2. Glossary Support & Hardcoded Translations: `src/meowth/glossary.py`

The glossary uses PokeAPI to fetch official translations of Pokémon, moves, abilities, etc.

- Somali is **not supported** by PokeAPI. `SUPPORTED_LANGUAGES[lang]["pokeapi_id"]` lookup will either fail or we need to pass a fallback/None.
- We must update `src/meowth/glossary.py` to handle cases where `pokeapi_id` is missing or None.
- **Conditional Logic**: We will add conditional logic: "if target lang is Somali (`so`), check hardcoded data stored in the repo instead of calling PokeAPI."
- This hardcoded data will ensure consistency for Pokémon names, move names, abilities, etc., avoiding the LLM translating them differently each time.

## 3. Translation Generation Scripts for PokeAPI Data

Since we need a hardcoded set of translations for Somali, we will create utility scripts to generate this data:
1. **Fetch Script**: A script that hits PokeAPI to generate lists of English terms (Pokémon names, move names, abilities, items, etc.) and saves them as JSON.
2. **Translate Script**: A mocked-up Python script that reads the English JSON, hits the OpenAI API to translate the terms into Somali, and saves the final translated JSON back into the repo.

This allows someone with an appropriate API key (better than the free tier) to run the script and generate the necessary static data files.

## 4. GUI Configuration Form: `src/meowth/gui/components/config_form.py`

The CustomTkinter GUI dropdowns require explicit mapping of display names to language codes.

- Update the `LANGUAGES` dictionary:
  ```python
  LANGUAGES = {
      "English": "en",
      "Chinese": "zh-Hans",
      "Spanish": "es",
      "French": "fr",
      "German": "de",
      "Italian": "it",
      "Somali": "so", # <-- ADD THIS
  }
  ```

## 5. Documentation updates

To reflect the new functionality, user-facing markdown docs should be updated.

- **`README.md`** (and translations like `README.zh.md`, etc.):
  - Update the "Six Language Support" to "Seven Language Support".
  - Add "Somali" - `so` to the "Supported Languages" list.

## 6. Potential Character Encoding Limitations: `src/meowth/charmap.py` & `src/meowth/pcs_codes.py`

Somali uses the Latin alphabet, but has some specific characters and digraphs. If it uses standard A-Z, it will be supported fine by the default `_build_from_pcs` logic in `src/meowth/charmap.py`. 
- If Somali text generation results in specific quotes or apostrophes (`’`, `‘`), they are already handled by `_CHAR_REPLACEMENTS` in `charmap.py`.

## Action Items Summary

1. Create a script to fetch PokeAPI terms and a script to translate them via OpenAI, saving as local JSON.
2. Modify `src/meowth/languages.py` to add Somali.
3. Modify `src/meowth/glossary.py` to bypass PokeAPI and load local JSON for Somali.
4. Modify `src/meowth/gui/components/config_form.py` to show Somali in GUI.
5. Update `README.md` to indicate Seven language support including Somali.