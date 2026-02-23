"""Load official Pokemon terminology from PokeAPI CSV files."""

import csv
from pathlib import Path

POKEAPI_DIR = Path(__file__).parent.parent.parent / "pokeapi-master" / "data" / "v2" / "csv"

# PokeAPI language IDs
LANG_EN = 9
LANG_ZH_HANS = 12  # Simplified Chinese
LANG_ZH_HANT = 4   # Traditional Chinese (fallback)

# CSV files and their name column
TERM_FILES = {
    "pokemon": ("pokemon_species_names.csv", "pokemon_species_id"),
    "moves": ("move_names.csv", "move_id"),
    "abilities": ("ability_names.csv", "ability_id"),
    "items": ("item_names.csv", "item_id"),
    "types": ("type_names.csv", "type_id"),
    "natures": ("nature_names.csv", "nature_id"),
}


class Glossary:
    def __init__(self, pokeapi_dir: Path = POKEAPI_DIR):
        self.en_to_zh: dict[str, str] = {}
        # Separate index for context matching: uppercase key → (original_en, zh)
        self._upper_index: dict[str, tuple[str, str]] = {}
        # Compact key index: uppercase with spaces/hyphens stripped
        # Handles GBA's 13-char move names like THUNDERPUNCH → Thunder Punch
        self._compact_index: dict[str, str] = {}
        # Try loading from pre-built JSON first, fall back to CSV
        json_path = Path(__file__).parent.parent.parent / "resources" / "glossary.json"
        if json_path.exists():
            self._load_json(json_path)
        else:
            self._load_all(pokeapi_dir)

    def _load_json(self, path: Path):
        """Load glossary from pre-built JSON file."""
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        self.en_to_zh = data.get("en_to_zh", {})
        # Build uppercase index and compact index
        for en, zh in self.en_to_zh.items():
            self._upper_index[en.upper()] = (en, zh)
            compact = en.upper().replace(" ", "").replace("-", "")
            self._compact_index[compact] = zh

    def _load_all(self, base_dir: Path):
        for category, (filename, id_col) in TERM_FILES.items():
            path = base_dir / filename
            if not path.exists():
                continue
            self._load_csv(path, id_col)

    def _load_csv(self, path: Path, id_col: str):
        """Load a PokeAPI names CSV and build en->zh mapping."""
        # Group by entity ID
        by_id: dict[int, dict[int, str]] = {}
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entity_id = int(row[id_col])
                lang_id = int(row["local_language_id"])
                name = row["name"].strip()
                if entity_id not in by_id:
                    by_id[entity_id] = {}
                by_id[entity_id][lang_id] = name

        # Build en -> zh mapping
        for entity_id, names in by_id.items():
            en_name = names.get(LANG_EN, "")
            zh_name = names.get(LANG_ZH_HANS) or names.get(LANG_ZH_HANT, "")
            if en_name and zh_name:
                self.en_to_zh[en_name] = zh_name
                self.en_to_zh[en_name.upper()] = zh_name
                self._upper_index[en_name.upper()] = (en_name, zh_name)
                compact = en_name.upper().replace(" ", "").replace("-", "")
                self._compact_index[compact] = zh_name

    def lookup(self, english: str) -> str | None:
        """Look up Chinese translation for an English term.

        Falls back to compact matching (no spaces/hyphens) for GBA's
        truncated names like THUNDERPUNCH → Thunder Punch.
        """
        result = self.en_to_zh.get(english) or self.en_to_zh.get(english.upper())
        if result:
            return result
        compact = english.upper().replace(" ", "").replace("-", "")
        return self._compact_index.get(compact)

    def apply_to_text(self, text: str) -> str:
        """Apply glossary replacements to text using word-boundary matching."""
        import re

        result = text
        # Sort by length (longest first) to avoid partial replacements
        for en, zh in sorted(self.en_to_zh.items(), key=lambda x: -len(x[0])):
            # Use word boundaries to avoid matching substrings inside other words
            # e.g. "Dig" should not match inside "Indigo"
            pattern = re.compile(r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])")
            result = pattern.sub(zh, result)
        return result

    def get_context_terms(self, text: str, limit: int = 20) -> dict[str, str]:
        """Find terms in text that have known translations (for LLM context).

        Uses the uppercase index for efficient case-insensitive matching.
        Only checks each unique term once against the text.
        """
        found: dict[str, str] = {}
        text_upper = text.upper()
        for upper_key, (en, zh) in self._upper_index.items():
            if upper_key in text_upper:
                found[en] = zh
                if len(found) >= limit:
                    break
        return found
