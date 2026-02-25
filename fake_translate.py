"""Fake translation: replace last letter of each word with '2'."""
import json
import re
from pathlib import Path

INPUT = Path("work/texts.json")
OUTPUT = Path("work/texts_translated.json")


def fake_translate(text: str) -> str:
    """Replace last alpha char of each word with '2', preserving control codes."""
    # Split on control codes like [player], \n, \\., \\p, etc. and keep them
    parts = re.split(r'(\[.*?\]|\\[.nplfBF])', text)
    result = []
    for part in parts:
        if re.match(r'\[.*?\]|\\[.nplfBF]', part):
            # control code, keep as-is
            result.append(part)
        else:
            # replace last alpha char of each word with '2'
            result.append(re.sub(r'([A-Za-z])\b', '2', part))
    return "".join(result)


data = json.loads(INPUT.read_text("utf-8"))

for entry in data["entries"]:
    original = entry["original"]
    # Strip surrounding quotes if present
    text = original.strip('"')
    entry["translated"] = fake_translate(text)

OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
print(f"Fake-translated {len(data['entries'])} entries → {OUTPUT}")
