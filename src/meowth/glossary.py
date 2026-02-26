"""Load official Pokemon terminology from PokeAPI CSV files."""

import csv
from pathlib import Path

from .languages import SUPPORTED_LANGUAGES

POKEAPI_DIR = Path(__file__).parent.parent.parent / "pokeapi" / "data" / "v2" / "csv"

# CSV files and their name column
TERM_FILES = {
    "pokemon": ("pokemon_species_names.csv", "pokemon_species_id"),
    "moves": ("move_names.csv", "move_id"),
    "abilities": ("ability_names.csv", "ability_id"),
    "items": ("item_names.csv", "item_id"),
    "types": ("type_names.csv", "type_id"),
    "natures": ("nature_names.csv", "nature_id"),
    "locations": ("location_names.csv", "location_id"),
    "regions": ("region_names.csv", "region_id"),
}


class Glossary:
    def __init__(
        self,
        pokeapi_dir: Path = POKEAPI_DIR,
        source_lang: str = "en",
        target_lang: str = "zh-Hans",
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.source_id = SUPPORTED_LANGUAGES[source_lang]["pokeapi_id"]
        self.target_id = SUPPORTED_LANGUAGES[target_lang]["pokeapi_id"]

        self.source_to_target: dict[str, str] = {}
        # Separate index for context matching: uppercase key → (original_source, target)
        self._upper_index: dict[str, tuple[str, str]] = {}
        # Compact key index: uppercase with spaces/hyphens stripped
        # Handles GBA's 13-char move names like THUNDERPUNCH → Thunder Punch
        self._compact_index: dict[str, str] = {}

        # Try loading from pre-built JSON first, fall back to CSV
        json_path = Path(__file__).parent.parent.parent / "resources" / f"glossary_{source_lang}_{target_lang}.json"
        if json_path.exists():
            self._load_json(json_path)
        else:
            self._load_all(pokeapi_dir)

    def _load_json(self, path: Path):
        """Load glossary from pre-built JSON file."""
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        self.source_to_target = data.get("source_to_target", {})
        # Build uppercase index and compact index
        for source, target in self.source_to_target.items():
            self._upper_index[source.upper()] = (source, target)
            compact = source.upper().replace(" ", "").replace("-", "")
            self._compact_index[compact] = target

    def _load_all(self, base_dir: Path):
        for category, (filename, id_col) in TERM_FILES.items():
            path = base_dir / filename
            if not path.exists():
                continue
            self._load_csv(path, id_col)

    def _load_csv(self, path: Path, id_col: str):
        """Load a PokeAPI names CSV and build source->target mapping."""
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

        # Build source -> target mapping
        for entity_id, names in by_id.items():
            source_name = names.get(self.source_id, "")
            target_name = names.get(self.target_id, "")
            if source_name and target_name:
                self.source_to_target[source_name] = target_name
                self.source_to_target[source_name.upper()] = target_name
                self._upper_index[source_name.upper()] = (source_name, target_name)
                compact = source_name.upper().replace(" ", "").replace("-", "")
                self._compact_index[compact] = target_name

    def lookup(self, source_text: str) -> str | None:
        """Look up target translation for a source term.

        Falls back to compact matching (no spaces/hyphens) for GBA's
        truncated names like THUNDERPUNCH → Thunder Punch.
        """
        result = self.source_to_target.get(source_text) or self.source_to_target.get(source_text.upper())
        if result:
            return result
        compact = source_text.upper().replace(" ", "").replace("-", "")
        return self._compact_index.get(compact)

    def apply_to_text(self, text: str) -> str:
        """Apply glossary replacements to text using word-boundary matching."""
        import re

        result = text
        # Sort by length (longest first) to avoid partial replacements
        for source, target in sorted(self.source_to_target.items(), key=lambda x: -len(x[0])):
            # Use word boundaries to avoid matching substrings inside other words
            # e.g. "Dig" should not match inside "Indigo"
            pattern = re.compile(r"(?<![A-Za-z])" + re.escape(source) + r"(?![A-Za-z])")
            result = pattern.sub(target, result)
        return result

    def get_context_terms(self, text: str, limit: int = 20) -> dict[str, str]:
        """Find terms in text that have known translations (for LLM context).

        Uses the uppercase index for efficient case-insensitive matching.
        Only checks each unique term once against the text.
        """
        found: dict[str, str] = {}
        text_upper = text.upper()
        for upper_key, (source, target) in self._upper_index.items():
            if upper_key in text_upper:
                found[source] = target
                if len(found) >= limit:
                    break
        return found
