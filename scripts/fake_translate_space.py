"""Fake translation: replace first letter after space with '2'."""
import json
import re
from pathlib import Path

INPUT = Path("work/text.json")
OUTPUT = Path("work/texts_translated.json")


def fake_translate(text: str) -> str:
    """Replace first letter after each space with '2', preserving control codes."""
    # Split on control codes like [player], \n, \\., \\p, etc. and keep them
    parts = re.split(r'(\[.*?\]|\\[.nplfBF])', text)
    result = []
    for part in parts:
        if re.match(r'\[.*?\]|\\[.nplfBF]', part):
            # control code, keep as-is
            result.append(part)
        else:
            # Replace first letter after space with '2'
            # Pattern: space followed by a letter (a-zA-Z)
            result.append(re.sub(r' ([a-zA-Z])', r' 2', part))
    return "".join(result)


data = json.loads(INPUT.read_text("utf-8"))

for entry in data["entries"]:
    original = entry["original"]
    # Strip surrounding quotes if present
    text = original.strip('"')
    entry["translated"] = fake_translate(text)

OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
print(f"Fake-translated {len(data['entries'])} entries → {OUTPUT}")
