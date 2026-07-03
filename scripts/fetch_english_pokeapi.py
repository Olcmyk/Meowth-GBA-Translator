#!/usr/bin/env python3
import csv
import json
from pathlib import Path
import sys

# English ID is 9
TARGET_LANG_ID = "9"

def fetch_terms():
    repo_root = Path(__file__).parent.parent
    pokeapi_dir = repo_root / "pokeapi" / "data" / "v2" / "csv"
    
    if not pokeapi_dir.exists():
        print("PokeAPI data not found. Make sure submodules are initialized.")
        sys.exit(1)

    term_files = {
        "pokemon": ("pokemon_species_names.csv", "pokemon_species_id"),
        "moves": ("move_names.csv", "move_id"),
        "abilities": ("ability_names.csv", "ability_id"),
        "items": ("item_names.csv", "item_id"),
        "types": ("type_names.csv", "type_id"),
        "natures": ("nature_names.csv", "nature_id"),
        "locations": ("location_names.csv", "location_id"),
        "regions": ("region_names.csv", "region_id"),
    }

    MAX_IDS = {
        "pokemon": 386,    # Up to Deoxys (Gen 3 end)
        "moves": 354,      # Up to Psycho Boost
        "abilities": 76,   # Up to Air Lock
        "items": 562,      # Gen 3 max item ID
        "types": 18,       # Base types
        "natures": 25,     # All natures
        "locations": 200,  # Kanto, Johto, Hoenn, Sevii
        "regions": 3       # Kanto, Johto, Hoenn
    }

    english_terms = {}
    term_categories = {}
    
    for category, (filename, id_col) in term_files.items():
        csv_path = pokeapi_dir / filename
        if not csv_path.exists():
            continue
            
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["local_language_id"] == TARGET_LANG_ID:
                    entity_id = int(row[id_col])
                    if entity_id <= MAX_IDS.get(category, 99999):
                        name = row["name"].strip()
                        if name:
                            english_terms[name] = "" # Empty translation as placeholder
                            term_categories[name] = category
                        
    output_path = repo_root / "resources" / "pokeapi_en_terms.json"
    
    data = {
        "terms": english_terms,
        "term_categories": term_categories
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Exported {len(english_terms)} English terms to {output_path}")

if __name__ == "__main__":
    fetch_terms()
