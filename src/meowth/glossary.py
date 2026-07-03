"""Load official Pokemon terminology from PokeAPI CSV files."""

import csv
from pathlib import Path

from .languages import SUPPORTED_LANGUAGES
from .resource_path import get_resource_path

POKEAPI_DIR = get_resource_path("pokeapi/data/v2/csv")

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

# Categories that should be included in LLM context (proper nouns only)
# These are terms that won't appear in everyday dialogue
CONTEXT_SAFE_CATEGORIES = {
    "pokemon",      # Pokemon names (BULBASAUR, PIKACHU)
    "locations",    # Location names (PALLET TOWN, VIRIDIAN CITY)
    "regions",      # Region names (KANTO, JOHTO)
}

# Categories excluded from context to avoid false matches
# These contain common words that might appear in dialogue
CONTEXT_UNSAFE_CATEGORIES = {
    "moves",        # Move names (bite, tackle, surf - common words!)
    "abilities",    # Ability names (overgrow, blaze)
    "items",        # Item names (potion, ball)
    "types",        # Type names (fire, water - very common!)
    "natures",      # Nature names (brave, timid - common adjectives!)
}

# Manual overrides per target language: source_text → target_text
# These take priority over PokeAPI glossary data
MANUAL_OVERRIDES: dict[str, dict[str, str]] = {
    "zh-Hans": {
        "Pokédex": "图鉴",
        "Pokedex": "图鉴",
        "POKEDEX": "图鉴",
        "POKéDEX": "图鉴",
    },
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
        # Separate index for context matching: uppercase key → (original_source, target, category)
        self._upper_index: dict[str, tuple[str, str, str]] = {}
        # Compact key index: uppercase with spaces/hyphens stripped
        # Handles GBA's 13-char move names like THUNDERPUNCH → Thunder Punch
        self._compact_index: dict[str, str] = {}
        # Category mapping: term → category
        self._term_category: dict[str, str] = {}

        # Try loading from pre-built JSON first, fall back to CSV
        json_path = Path(__file__).parent.parent.parent / "resources" / f"glossary_{source_lang}_{target_lang}.json"
        if json_path.exists():
            self._load_json(json_path)
        elif target_lang == "so":
            raise RuntimeError(f"Pre-built JSON glossary required for Somali ({json_path.name}) not found. Please generate it using the translation scripts.")
        else:
            self._load_all(pokeapi_dir)

        # Apply manual overrides (highest priority, overwrite PokeAPI data)
        overrides = MANUAL_OVERRIDES.get(target_lang, {})
        for source, target in overrides.items():
            self.source_to_target[source] = target
            self._upper_index[source.upper()] = (source, target, "manual")
            self._term_category[source] = "manual"
            compact = source.upper().replace(" ", "").replace("-", "")
            self._compact_index[compact] = target

    def _load_json(self, path: Path):
        """Load glossary from pre-built JSON file."""
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        self.source_to_target = data.get("source_to_target", {})
        term_categories = data.get("term_categories", {})

        # Build uppercase index and compact index
        for source, target in self.source_to_target.items():
            category = term_categories.get(source, "unknown")
            self._upper_index[source.upper()] = (source, target, category)
            self._term_category[source] = category
            compact = source.upper().replace(" ", "").replace("-", "")
            self._compact_index[compact] = target


    def _load_all(self, base_dir: Path):
        for category, (filename, id_col) in TERM_FILES.items():
            path = base_dir / filename
            if not path.exists():
                continue
            self._load_csv(path, id_col, category)

    def _load_csv(self, path: Path, id_col: str, category: str):
        """Load a PokeAPI names CSV and build source->target mapping."""
        # Check if the target language even has a pokeapi_id
        if self.target_id is None:
            return
            
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
                self._upper_index[source_name.upper()] = (source_name, target_name, category)
                self._term_category[source_name] = category
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

    def add_term(self, source: str, target: str, category: str = "dynamic") -> None:
        """Add a dynamic term to the glossary (e.g. from translated tables)."""
        self.source_to_target[source] = target
        self._upper_index[source.upper()] = (source, target, category)
        self._term_category[source] = category
        compact = source.upper().replace(" ", "").replace("-", "")
        self._compact_index[compact] = target

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

        Only includes proper nouns (Pokemon names, locations, regions) to avoid
        false matches with common words like "bite" (move name) or "fire" (type).

        Uses the uppercase index for efficient case-insensitive matching.
        Only checks each unique term once against the text.
        """
        found: dict[str, str] = {}
        text_upper = text.upper()
        for upper_key, (source, target, category) in self._upper_index.items():
            # Include safe categories (proper nouns) and manual overrides
            if category not in CONTEXT_SAFE_CATEGORIES and category not in ("manual", "dynamic"):
                continue
            if upper_key in text_upper:
                found[source] = target
                if len(found) >= limit:
                    break
        return found
