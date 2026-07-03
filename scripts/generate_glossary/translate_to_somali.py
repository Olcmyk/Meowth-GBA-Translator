"""Mock script to translate English terms to Somali using OpenAI."""


import json
import os
from pathlib import Path

# This is a mock translation script that demonstrates how to generate
# a static glossary mapping file for Somali.
# Since Somali isn't in PokeAPI, we translate the English terms using an LLM.

def translate_to_somali():
    input_path = Path(__file__).parent / "english_terms.json"
    
    if not input_path.exists():
        print("Run fetch_english_terms.py first.")
        return
        
    with open(input_path, "r", encoding="utf-8") as f:
        english_terms = json.load(f)
        
    print("Mocking translation to Somali...")
    # In a real scenario, you'd use the openai python client here:
    # client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    source_to_target = {}
    term_categories = {}
    
    for category, terms in english_terms.items():
        print(f"Translating {len(terms)} items in {category}...")
        for term in terms:
            # MOCK TRANSLATION: Just append " (So)" to the English term
            translated = f"{term} (So)"
            source_to_target[term] = translated
            term_categories[term] = category
            
    # Save the result in the format expected by Glossary._load_json
    output_data = {
        "source_to_target": source_to_target,
        "term_categories": term_categories
    }
    
    # Save directly to resources folder where meowth/glossary.py expects it
    resources_dir = Path(__file__).parent.parent.parent / "resources"
    resources_dir.mkdir(exist_ok=True)
    
    output_path = resources_dir / "glossary_en_so.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Saved mock Somali glossary to {output_path}")

if __name__ == "__main__":
    translate_to_somali()
