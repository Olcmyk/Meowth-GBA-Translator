"""Fetch English terms from PokeAPI CSVs to be used for generating hardcoded glossaries."""

import csv
import json
from pathlib import Path
import sys

# Try to append src so we can reuse POKEAPI_DIR and TERM_FILES
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

try:
    from meowth.glossary import POKEAPI_DIR, TERM_FILES
except ImportError:
    print("Could not import Meowth codebase. Run from repository root.")
    sys.exit(1)

def fetch_english_terms():
    """Extract English names from PokeAPI CSVs and save to JSON."""
    english_id = 9
    terms_by_category = {}

    for category, (filename, id_col) in TERM_FILES.items():
        path = POKEAPI_DIR / filename
        if not path.exists():
            print(f"Warning: {filename} not found.")
            continue
            
        terms_by_category[category] = []
        
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row["local_language_id"]) == english_id:
                    terms_by_category[category].append(row["name"].strip())
                    
    output_path = Path(__file__).parent / "english_terms.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(terms_by_category, f, indent=2, ensure_ascii=False)
        
    print(f"Exported English terms to {output_path}")

if __name__ == "__main__":
    fetch_english_terms()
