"""Load official Pokemon terminology from PokeAPI CSV files."""

import csv
from pathlib import Path

from .languages import get_pokeapi_id

POKEAPI_DIR = Path(__file__).parent.parent.parent / "pokeapi" / "data" / "v2" / "csv"

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
    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "zh-Hans",
        pokeapi_dir: Path = POKEAPI_DIR,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.source_to_target: dict[str, str] = {}
        # Separate index for context matching: uppercase key → (original_source, target)
        self._upper_index: dict[str, tuple[str, str]] = {}
        # Compact key index: uppercase with spaces/hyphens stripped
        self._compact_index: dict[str, str] = {}

        # For en→zh-Hans, try pre-built JSON first (existing behavior)
        json_path = Path(__file__).parent.parent.parent / "resources" / "glossary.json"
        if source_lang == "en" and target_lang == "zh-Hans" and json_path.exists():
            self._load_json(json_path)
        else:
            self._load_all(pokeapi_dir)

    def _load_json(self, path: Path):
        """Load glossary from pre-built JSON file (en→zh-Hans only)."""
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        self.source_to_target = data.get("en_to_zh", {})
        for src, tgt in self.source_to_target.items():
            self._upper_index[src.upper()] = (src, tgt)
            compact = src.upper().replace(" ", "").replace("-", "")
            self._compact_index[compact] = tgt

    def _load_all(self, base_dir: Path):
        source_id = get_pokeapi_id(self.source_lang)
        target_id = get_pokeapi_id(self.target_lang)
        for category, (filename, id_col) in TERM_FILES.items():
            path = base_dir / filename
            if not path.exists():
                continue
            self._load_csv(path, id_col, source_id, target_id)

    def _load_csv(self, path: Path, id_col: str, source_id: int, target_id: int):
        """Load a PokeAPI names CSV and build source→target mapping."""
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

        for entity_id, names in by_id.items():
            src_name = names.get(source_id, "")
            tgt_name = names.get(target_id, "")
            if src_name and tgt_name:
                self.source_to_target[src_name] = tgt_name
                self.source_to_target[src_name.upper()] = tgt_name
                self._upper_index[src_name.upper()] = (src_name, tgt_name)
                compact = src_name.upper().replace(" ", "").replace("-", "")
                self._compact_index[compact] = tgt_name

    def lookup(self, term: str) -> str | None:
        """Look up target-language translation for a source-language term.

        Falls back to compact matching (no spaces/hyphens) for GBA's
        truncated names like THUNDERPUNCH → Thunder Punch.
        """
        result = self.source_to_target.get(term) or self.source_to_target.get(term.upper())
        if result:
            return result
        compact = term.upper().replace(" ", "").replace("-", "")
        return self._compact_index.get(compact)

    def apply_to_text(self, text: str) -> str:
        """Apply glossary replacements to text using word-boundary matching."""
        import re

        result = text
        for src, tgt in sorted(self.source_to_target.items(), key=lambda x: -len(x[0])):
            pattern = re.compile(r"(?<![A-Za-z])" + re.escape(src) + r"(?![A-Za-z])")
            result = pattern.sub(tgt, result)
        return result

    def get_context_terms(self, text: str, limit: int = 20) -> dict[str, str]:
        """Find terms in text that have known translations (for LLM context).

        Uses the uppercase index for efficient case-insensitive matching.
        """
        found: dict[str, str] = {}
        text_upper = text.upper()
        for upper_key, (src, tgt) in self._upper_index.items():
            if upper_key in text_upper:
                found[src] = tgt
                if len(found) >= limit:
                    break
        return found
