"""Main translation pipeline orchestration."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from .charmap import Charmap
from .control_codes import protect, restore
from .font_patch import apply_font_patch
from .glossary import Glossary
from .rom_writer import RomWriter
from .translator import Translator

# ---------------------------------------------------------------------------
# Format conversion: MeowthBridge {"entries":[...]} → {"tables":[], "free_texts":[]}
# ---------------------------------------------------------------------------
TABLE_CATEGORIES = {
    "pokemon_names", "move_names", "ability_names", "nature_names",
    "type_names", "item_names", "trainer_classes", "map_names",
}


def convert_format(data: dict) -> dict:
    """Convert MeowthBridge entries format to tables + free_texts format."""
    if "tables" in data:
        return data
    entries = data["entries"]
    tables_by_cat: dict[str, list] = {}
    free_texts: list = []
    for e in entries:
        cat = e.get("category", "")
        if cat in TABLE_CATEGORIES:
            tables_by_cat.setdefault(cat, []).append(e)
        else:
            free_texts.append(e)
    return {
        "tables": [{"category": c, "entries": es} for c, es in tables_by_cat.items()],
        "free_texts": free_texts,
    }

# ---------------------------------------------------------------------------
# Hardcoded translation overrides
# ---------------------------------------------------------------------------
# Some intro/Oak texts need precise pagination that the auto-wrap can't
# produce from the AI translation alone.  Each value is the final wrapped
# string (with \n / \p already placed) — it bypasses wrap_text().
_HARDCODED_TRANSLATIONS: dict[str, str] = {
    # ---- 冒险介绍 第1页 ----
    "scr_02219": (
        "你将成为主角，\n探索宝可梦的世界！"
        "\n\n通过与人们交谈并解开谜题，\n新的道路将为你敞开。"
        "\n\n与你出色的宝可梦一起，\n朝着目标努力吧！"
    ),
    # ---- 大木博士出场 ----
    "scr_02329": (
        "你好啊！\n很高兴见到你！"
        "\n\n欢迎来到宝可梦火红VX！"
        "\n\n我叫大木。"
        "\n\n人们亲切地称呼我为\n宝可梦博士。\n\n"
    ),
    "scr_02330": "这个世界",
    "scr_02331": "到处都栖息着被称为\n宝可梦的生物。\n\n",
    "scr_02332": (
        "对有些人来说，宝可梦是宠物。\n也有人用它们来对战。"
        "\n\n至于我自己……"
        "\n\n我把研究宝可梦当作职业。"
    ),
    "scr_02333": "不过首先，\n请告诉我一些关于你自己的事。",
    "scr_02334": "先从你的名字开始吧。\n你叫什么名字？",
    "scr_02335": "好的……\n\n原来你叫[player]。",
    "scr_02336": (
        "这是我的孙子。"
        "\n\n从你们还是婴儿的时候起，\n他就一直是你的劲敌。"
        "\n\n呃，他叫什么名字来着？"
    ),
    "scr_02339": "没错！我想起来了！\n他的名字是[rival]！",
    "scr_02340": (
        "[player]！"
        "\n\n属于你自己的宝可梦传奇\n即将展开！"
        "\n\n充满梦想与冒险的宝可梦世界\n正等待着你！出发吧！"
    ),
}


class Pipeline:
    def __init__(
        self,
        charmap: Charmap | None = None,
        glossary: Glossary | None = None,
        translator: Translator | None = None,
    ):
        self.charmap = charmap or Charmap()
        self.glossary = glossary or Glossary()
        self.translator = translator or Translator()

    def translate_texts(
        self, texts_path: Path, output_path: Path, batch_size: int = 30
    ) -> Path:
        """Translate extracted texts JSON."""
        data = json.loads(texts_path.read_text(encoding="utf-8"))
        data = convert_format(data)

        # Translate table entries
        for table in data["tables"]:
            self._translate_table(table)

        # Translate free texts in batches
        free_texts = data["free_texts"]
        for i in range(0, len(free_texts), batch_size):
            batch = free_texts[i : i + batch_size]
            self._translate_free_batch(batch)
            print(
                f"  Translated free text batch {i // batch_size + 1}"
                f"/{(len(free_texts) + batch_size - 1) // batch_size}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return output_path

    def _translate_table(self, table: dict):
        """Translate a table's entries using glossary lookup."""
        category = table["category"]
        for entry in table["entries"]:
            original = entry["original"].strip('"')
            # Try glossary lookup first
            zh = self.glossary.lookup(original)
            if zh:
                # Validate against charmap
                ok, bad = self.charmap.can_encode(zh)
                if ok:
                    entry["translated"] = zh
                    continue
            # For descriptions, use LLM
            if "description" in category:
                protected, codes = protect(original)
                glossary_ctx = self._format_glossary(original)
                results = self.translator.translate_batch(
                    [protected], glossary_ctx
                )
                translated = restore(results[0], codes)
                entry["translated"] = translated
            elif zh:
                # Had a glossary match but with bad chars, use it anyway
                entry["translated"] = zh
            else:
                # No translation available, keep original
                entry["translated"] = original

    def _translate_free_batch(self, batch: list[dict]):
        """Translate a batch of free text entries via LLM."""
        # Apply hardcoded overrides first
        remaining = []
        for entry in batch:
            entry_id = entry.get("id", "")
            if entry_id in _HARDCODED_TRANSLATIONS:
                entry["translated"] = _HARDCODED_TRANSLATIONS[entry_id]
            else:
                remaining.append(entry)

        if not remaining:
            return

        originals = [e["original"] for e in remaining]

        # Protect control codes
        protected_list = []
        codes_list = []
        for text in originals:
            protected, codes = protect(text)
            protected_list.append(protected)
            codes_list.append(codes)

        # Build glossary context from all texts in batch
        all_text = " ".join(originals)
        glossary_ctx = self._format_glossary(all_text)

        # Translate
        results = self.translator.translate_batch(protected_list, glossary_ctx)

        # Restore control codes
        for i, entry in enumerate(remaining):
            translated = restore(results[i], codes_list[i])
            entry["translated"] = translated

    def _format_glossary(self, text: str) -> str:
        terms = self.glossary.get_context_terms(text)
        if not terms:
            return ""
        return "\n".join(f"  {en} = {zh}" for en, zh in terms.items())

    @staticmethod
    def _fix_paragraph_waits(entry: dict):
        """Ensure translation preserves paragraph waits from original.

        HMA exports: \\n\\n = paragraph wait (0xFB), single \\n = newline (0xFE).
        If original has paragraph waits but translation lost them,
        distribute them evenly through the translation.
        """
        orig = entry["original"]
        trans = entry.get("translated", "")
        if not trans or trans == orig:
            return

        # Count paragraph waits by splitting on \n\n (non-overlapping)
        orig_paras = len(orig.split("\n\n")) - 1
        trans_paras = len(trans.split("\n\n")) - 1

        if orig_paras <= 0 or trans_paras >= orig_paras:
            return

        needed = orig_paras - trans_paras

        # Split on \n\n first to preserve existing paragraph waits,
        # then look for single \n within each paragraph to upgrade.
        paragraphs = trans.split("\n\n")
        # Collect (paragraph_idx, line_idx) for each single-\n join point
        upgrade_candidates: list[tuple[int, int]] = []
        for p_idx, para in enumerate(paragraphs):
            lines = para.split("\n")
            for l_idx in range(len(lines) - 1):
                upgrade_candidates.append((p_idx, l_idx))

        if upgrade_candidates:
            # Pick evenly spaced positions to upgrade
            step = len(upgrade_candidates) / (needed + 1)
            upgrade_set: set[tuple[int, int]] = set()
            for j in range(needed):
                idx = min(int((j + 1) * step), len(upgrade_candidates) - 1)
                upgrade_set.add(upgrade_candidates[idx])

            # Rebuild each paragraph with upgrades applied
            new_paragraphs = []
            for p_idx, para in enumerate(paragraphs):
                lines = para.split("\n")
                parts = []
                for l_idx, line in enumerate(lines):
                    parts.append(line)
                    if l_idx < len(lines) - 1:
                        if (p_idx, l_idx) in upgrade_set:
                            parts.append("\n\n")
                        else:
                            parts.append("\n")
                new_paragraphs.append("".join(parts))
            entry["translated"] = "\n\n".join(new_paragraphs)
        else:
            # No single newlines to upgrade — insert paragraph waits
            # at evenly spaced character positions
            total_len = len(trans)
            step = total_len / (needed + 1)
            insert_positions = sorted(
                [int((j + 1) * step) for j in range(needed)], reverse=True
            )
            for pos in insert_positions:
                trans = trans[:pos] + "\n\n" + trans[pos:]
            entry["translated"] = trans

    def build_rom(
        self,
        original_rom: Path,
        translations_path: Path,
        output_path: Path,
    ) -> Path:
        """Build final Chinese ROM."""
        data = json.loads(translations_path.read_text(encoding="utf-8"))
        data = convert_format(data)

        writer = RomWriter(self.charmap)

        # 1. Load and expand ROM
        print("  Loading ROM...")
        rom = writer.load_rom(original_rom)
        rom = writer.expand_rom(rom)
        print(f"  ROM expanded to {len(rom) // (1024*1024)}MB")

        # 2. Apply font patch
        print("  Applying font patch...")
        temp_rom = output_path.parent / "temp_fontpatch.gba"
        writer.save_rom(rom, temp_rom)
        apply_font_patch(temp_rom, temp_rom)
        rom = writer.load_rom(temp_rom)
        temp_rom.unlink(missing_ok=True)
        print("  Font patch applied")

        # 3. Collect all entries for injection
        all_entries = []
        for table in data["tables"]:
            for entry in table["entries"]:
                if "translated" in entry:
                    all_entries.append(entry)
        for entry in data["free_texts"]:
            if "translated" in entry:
                self._fix_paragraph_waits(entry)
                all_entries.append(entry)

        # 3b. Load manual entries (texts not extracted by HMA)
        manual_path = Path(__file__).parent / "manual_entries.json"
        if manual_path.exists():
            manual = json.loads(manual_path.read_text(encoding="utf-8"))
            all_entries.extend(manual)
            print(f"  Added {len(manual)} manual entries")

        # 4. Inject texts
        print(f"  Injecting {len(all_entries)} translated texts...")
        rom, stats = writer.inject_texts(rom, all_entries)
        print(
            f"  Done: {stats['in_place']} in-place, "
            f"{stats['relocated']} relocated, {stats['skipped']} skipped, "
            f"{stats.get('skipped_partial_ptrs', 0)} partial-ptr skipped, "
            f"{stats.get('unsafe_ptrs', 0)} unsafe ptrs filtered"
        )

        # 5. Save
        writer.save_rom(rom, output_path)
        print(f"  Saved: {output_path}")
        return output_path

    @staticmethod
    def find_meowth_bridge() -> Path:
        """Locate the MeowthBridge executable."""
        base = Path(__file__).parent.parent / "MeowthBridge" / "bin"
        for profile in ("Release", "Debug"):
            exe = base / profile / "net8.0" / "MeowthBridge"
            if exe.exists():
                return exe
        raise FileNotFoundError(
            "MeowthBridge executable not found. "
            "Build it first: dotnet build src/MeowthBridge -c Release"
        )

    @staticmethod
    def extract_texts(rom_path: Path, output_path: Path) -> Path:
        """Extract texts from ROM using MeowthBridge."""
        exe = Pipeline.find_meowth_bridge()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [str(exe), "extract", str(rom_path), "-o", str(output_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"MeowthBridge failed (exit {result.returncode}):\n{result.stderr}"
            )
        if not output_path.exists():
            raise RuntimeError(f"MeowthBridge did not produce {output_path}")
        return output_path

    def run_full(
        self,
        rom_path: Path,
        output_dir: Path,
        work_dir: Path,
    ) -> Path:
        """Run the full translation pipeline: extract → translate → build."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        texts_path = work_dir / "texts.json"
        translated_path = work_dir / "texts_translated.json"
        output_path = output_dir / f"firered_cn_{timestamp}.gba"

        print("[1/3] Extracting texts from ROM...")
        self.extract_texts(rom_path, texts_path)

        print("[2/3] Translating texts...")
        self.translate_texts(texts_path, translated_path)

        print("[3/3] Building ROM...")
        self.build_rom(rom_path, translated_path, output_path)

        print(f"Complete: {output_path}")
        return output_path
