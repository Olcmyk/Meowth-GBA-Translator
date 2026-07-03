#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
import time

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install google-genai: pip install google-genai")
    sys.exit(1)

def translate_batch(client, batch_dict, retries=3):
    # batch_dict is a dictionary mapping term -> category
    system_prompt = (
        "You are a professional translator specializing in video game localization, specifically Pokémon. "
        "Create Somali localizations for various terms based on their category:\n"
        "- For Pokémon names: Ask yourself 'If this Pokémon was originally created in Somali, what clever, meaningful name would it have?'. Focus heavily on inventing new names that capture the Pokémon's meaning, animal/object inspiration, or elemental typing using Somali root words. "
        "CRITICAL: ALL Pokémon names MUST be 10 characters or less. Do NOT exceed 10 characters under any circumstances. "
        "Recreate wordplay where possible. For extremely important or iconic Pokémon (like legendaries), phonetic adaptation is acceptable, but if meaning can be imparted natively, prefer that. "
        "Keep evolutionary families consistent and preserve relationships. Always favor memorable, native-sounding invented names over literal descriptive phrases.\n"
        "- For Moves, Abilities, and Items: Make them punchy, descriptive, and localized for a gaming context, preserving the original flavor. Avoid overly literal academic translations; make them sound like cool fantasy/game terms in Somali. Keep them under 13 characters if possible.\n"
        "- For Regions and Locations: Adapt place names naturally. Keep suffixes like City, Town, Region consistent with Somali geographical terms, or phonologically adapt the English ones if they sound better.\n"
        "Always return ONLY valid JSON where keys are the exact English terms provided and values are the Somali translations."
    )
    
    prompt = (
        "Translate the following Pokémon terminology from English to Somali following the system guidelines.\n"
        "The terms are provided in a JSON object mapping the English term to its category (e.g. pokemon, moves, abilities, items, locations, regions).\n"
        "Return ONLY a valid JSON object where keys are the exact English terms provided and values are the Somali translations.\n\n"
        f"Terms to translate:\n{json.dumps(batch_dict, indent=2)}"
    )
    
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.4,
                ),
            )
            content = response.text
            return json.loads(content)
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            if attempt == retries - 1:
                return {term: f"{term} (ERROR)" for term in batch_dict.keys()}
            time.sleep(2)

def load_env_file():
    """Load environment variables from a .env file in the repository root."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    try:
                        key, val = line.strip().split("=", 1)
                        os.environ[key.strip()] = val.strip().strip("'\"")
                    except ValueError:
                        pass

def translate_terms():
    is_test_mode = "--test" in sys.argv
    
    load_env_file()
    api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set it in your terminal, or create a .env file in the project root with: GOOGLE_API_KEY=your_key")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    repo_root = Path(__file__).parent.parent
    input_path = repo_root / "resources" / "pokeapi_en_terms.json"
    output_path = repo_root / "resources" / "glossary_en_so.json"
    
    if not input_path.exists():
        print(f"Input file {input_path} not found. Run fetch_english_pokeapi.py first.")
        sys.exit(1)
        
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    terms_dict = data.get("terms", {})
    term_categories = data.get("term_categories", {})
    
    all_terms = list(terms_dict.keys())
    total_terms = len(all_terms)
    
    # Check if we already have partial translations
    source_to_target = {}
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                source_to_target = existing_data.get("source_to_target", {})
                print(f"Loaded {len(source_to_target)} existing translations.")
        except Exception:
            pass
            
    # Filter terms that are already translated or were mocked
    pending_terms = [t for t in all_terms if t not in source_to_target or "(SO)" in source_to_target[t] or "(ERROR)" in source_to_target[t]]
    
    if not pending_terms:
        print("All terms are already translated.")
        return
        
    print(f"Starting translation for {len(pending_terms)} terms...")
    if is_test_mode:
        print("TEST MODE: Will only process 1 batch of 50 terms.")
    
    batch_size = 50
    for i in range(0, len(pending_terms), batch_size):
        batch = pending_terms[i:i+batch_size]
        batch_dict = {term: term_categories.get(term, "unknown") for term in batch}
        
        print(f"Translating batch {i//batch_size + 1}/{(len(pending_terms) + batch_size - 1)//batch_size} (Terms {i+1} to {min(i+batch_size, len(pending_terms))})...")
        
        translations = translate_batch(client, batch_dict)
        
        for term in batch:
            source_to_target[term] = translations.get(term, f"{term} (ERROR)")
            
        # Save progress after every batch to prevent data loss on crash
        output_data = {
            "source_to_target": source_to_target,
            "term_categories": term_categories
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
            
        # Small delay to avoid rate limits
        time.sleep(2)
        
        if is_test_mode:
            print("Test mode enabled: stopping after one batch.")
            break
        
    print(f"Finished translating {total_terms} total terms and saved to {output_path}")

if __name__ == "__main__":
    translate_terms()
