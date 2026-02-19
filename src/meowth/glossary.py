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
        self._load_all(pokeapi_dir)

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

    def lookup(self, english: str) -> str | None:
        """Look up Chinese translation for an English term."""
        return self.en_to_zh.get(english) or self.en_to_zh.get(english.upper())

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
