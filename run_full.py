"""Full pipeline: convert format, translate, inject."""
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

from meowth.charmap import Charmap
from meowth.config import load_config
from meowth.control_codes import protect, restore
from meowth.glossary import Glossary
from meowth.languages import is_cjk_language
from meowth.rom_writer import RomWriter
from meowth.translator import Translator
from meowth.pipeline import _HARDCODED_TRANSLATIONS, detect_game

# ---- Config ----
cfg = load_config()

# ---- Game detection ----
if len(sys.argv) > 1:
    ROM_PATH = Path(sys.argv[1])
else:
    ROM_PATH = Path("testgba/firered_en.gba")

game = detect_game(ROM_PATH)
if game == "unknown":
    print(f"Warning: could not detect game from {ROM_PATH}, defaulting to firered")
    game = "firered"
else:
    print(f"Detected game: {game}")

# Per-game output paths
lang_suffix = cfg.target_language.replace("-", "")

TEXTS_PATH = Path("work/texts.json")
TRANSLATED_PATH = Path("work/texts_translated.json")
OUTPUT_PATH = Path("outputs") / f"{game}_{lang_suffix}.gba"

# ---- Step 1: Convert MeowthBridge format to tables + free_texts ----
print("=" * 60)
print("[1/3] 转换数据格式...")
raw = json.loads(TEXTS_PATH.read_text("utf-8"))
entries = raw["entries"]

TABLE_CATEGORIES = {
    "pokemon_names", "move_names", "ability_names", "nature_names",
    "type_names", "item_names", "trainer_classes", "map_names",
}

tables_by_cat: dict[str, list] = {}
free_texts: list = []

for e in entries:
    cat = e.get("category", "")
    if cat in TABLE_CATEGORIES:
        tables_by_cat.setdefault(cat, []).append(e)
    else:
        free_texts.append(e)

tables = [{"category": cat, "entries": ents} for cat, ents in tables_by_cat.items()]
data = {"tables": tables, "free_texts": free_texts}
print(f"  表格: {sum(len(t['entries']) for t in tables)} 条 ({len(tables)} 类)")
print(f"  自由文本: {len(free_texts)} 条")

# ---- Step 2: Translate ----
print("=" * 60)
print("[2/3] 翻译文本...")

glossary = Glossary(source_lang=cfg.source_language, target_lang=cfg.target_language)
translator = Translator(
    api_key=cfg.api_key,
    model=cfg.model,
    base_url=cfg.base_url,
    source_lang=cfg.source_language,
    target_lang=cfg.target_language,
)
charmap = Charmap()

# 2a. Translate table entries (glossary first, then LLM for descriptions)
for table in tables:
    cat = table["category"]
    for entry in table["entries"]:
        original = entry["original"].strip('"')
        tgt = glossary.lookup(original)
        if tgt:
            ok, _ = charmap.can_encode(tgt)
            if ok:
                entry["translated"] = tgt
                continue
        # Keep original for short names (no LLM needed)
        entry["translated"] = original
    translated_count = sum(1 for e in table["entries"] if e.get("translated") != e["original"].strip('"'))
    print(f"  {cat}: {translated_count}/{len(table['entries'])} 条翻译")

# 2b. Translate free texts in batches
BATCH_SIZE = 30
total = len(free_texts)
use_hardcoded = cfg.target_language == "zh-Hans" and game == "firered"

for i in range(0, total, BATCH_SIZE):
    batch = free_texts[i:i + BATCH_SIZE]

    # Check hardcoded overrides first (FireRed + zh-Hans only)
    remaining = []
    for entry in batch:
        eid = entry.get("id", "")
        if use_hardcoded and eid in _HARDCODED_TRANSLATIONS:
            entry["translated"] = _HARDCODED_TRANSLATIONS[eid]
        else:
            remaining.append(entry)

    if not remaining:
        print(f"  批次 {i // BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1) // BATCH_SIZE} (全部硬编码)")
        continue

    originals = [e["original"] for e in remaining]

    # Protect control codes
    protected_list = []
    codes_list = []
    for text in originals:
        p, c = protect(text)
        protected_list.append(p)
        codes_list.append(c)

    # Glossary context
    all_text = " ".join(originals)
    terms = glossary.get_context_terms(all_text)
    glossary_ctx = "\n".join(f"  {src} = {tgt}" for src, tgt in terms.items()) if terms else ""

    # Translate
    results = translator.translate_batch(protected_list, glossary_ctx)

    # Restore
    for j, entry in enumerate(remaining):
        entry["translated"] = restore(results[j], codes_list[j])

    batch_num = i // BATCH_SIZE + 1
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  批次 {batch_num}/{total_batches} 完成 ({len(remaining)} 条翻译)")

    # Save progress
    TRANSLATED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

# Final save
TRANSLATED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
print(f"  翻译结果已保存: {TRANSLATED_PATH}")

# ---- Step 3: Build ROM ----
print("=" * 60)
print("[3/3] 构建 ROM...")

# Collect all translated entries
all_entries = []
for table in data["tables"]:
    for entry in table["entries"]:
        if "translated" in entry:
            all_entries.append(entry)
for entry in data["free_texts"]:
    if "translated" in entry:
        all_entries.append(entry)

print(f"  共 {len(all_entries)} 条待写入")

writer = RomWriter(charmap, game=game)
rom = writer.load_rom(ROM_PATH)
rom = writer.expand_rom(rom)
print(f"  ROM 扩展到 {len(rom) // (1024*1024)}MB")

overrides = _HARDCODED_TRANSLATIONS if use_hardcoded else None
rom, stats = writer.inject_texts(rom, all_entries, overrides=overrides)
print(f"  写入: {stats['in_place']} in-place, {stats['relocated']} relocated, "
      f"{stats['skipped']} skipped, {stats['errors']} errors")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
writer.save_rom(rom, OUTPUT_PATH)
print(f"  输出: {OUTPUT_PATH}")
print("=" * 60)
print("完成！")
