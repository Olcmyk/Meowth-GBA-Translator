"""Main translation pipeline orchestration."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from .charmap import Charmap
from .control_codes import protect, restore
from .font_patch import apply_font_patch
from .glossary import Glossary
from .languages import is_cjk_language
from .pcs_codes import FD_MACROS
from .rom_writer import RomWriter
from .text_wrap import wrap_text
from .translator import Translator

# ---------------------------------------------------------------------------
# Game detection from ROM header
# ---------------------------------------------------------------------------
# GBA ROM header bytes 0xAC-0xAF contain the 4-byte game code.
_GAME_CODES: dict[str, str] = {
    "BPRE": "firered",
    "BPGE": "leafgreen",
    "BPEE": "emerald",
    "AXVE": "ruby",
    "AXPE": "sapphire",
}


def detect_game(rom_path: Path) -> str:
    """Detect game type from GBA ROM header (bytes 0xAC-0xAF).

    Returns one of: "firered", "leafgreen", "emerald", "ruby", "sapphire", "unknown".
    """
    with open(rom_path, "rb") as f:
        f.seek(0xAC)
        code = f.read(4).decode("ascii", errors="replace")
    return _GAME_CODES.get(code, "unknown")

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

# Manual translations for trainer classes not in the PokeAPI glossary
_TRAINER_CLASS_OVERRIDES: dict[str, str] = {
    "RIVAL": "劲敌",
}


def _strip_llm_newlines(text: str) -> str:
    """Remove literal newlines inserted by the LLM for formatting.

    After control-code restoration, semantic breaks are already present as
    real \\n\\n (paragraph) or \\n (semantic newline).  Any *additional*
    literal newlines were injected by the LLM to wrap its own output and
    should be removed so that wrap_text() can re-wrap at the correct
    Chinese line width.

    Strategy: replace single literal newlines (not part of \\n\\n) with
    empty string (join the text), preserving \\n\\n paragraph breaks.
    """
    # Protect \n\n paragraph breaks
    _PARA = "\x00PARA\x00"
    text = text.replace("\n\n", _PARA)
    # Remove remaining single \n (LLM formatting artifacts)
    text = text.replace("\n", "")
    # Restore paragraph breaks
    text = text.replace(_PARA, "\n\n")
    return text


def _postprocess_fd_macros(json_path: Path):
    """Replace HMA's raw FD escape sequences (e.g. \\\\05) with named macros (e.g. [kun]).

    HMA only recognises a few FD codes ([player], [rival], etc.).
    Any FD code it doesn't know gets output as \\\\XX.
    We patch those using our FD_MACROS table so every extraction is consistent.
    """
    # Build replacement map: only for codes HMA doesn't already handle
    _HMA_KNOWN = {0x01, 0x02, 0x03, 0x04, 0x06}  # player, buffer1-3, rival
    replacements = {}
    for code, name in FD_MACROS.items():
        if code not in _HMA_KNOWN:
            # In JSON the text looks like \\\\05 (escaped backslashes + hex)
            replacements[f"\\\\\\\\{code:02X}"] = name
    if not replacements:
        return
    text = json_path.read_text(encoding="utf-8")
    for raw, macro in replacements.items():
        text = text.replace(raw, macro)
    json_path.write_text(text, encoding="utf-8")


class Pipeline:
    def __init__(
        self,
        charmap: Charmap | None = None,
        glossary: Glossary | None = None,
        translator: Translator | None = None,
        game: str = "firered",
        source_lang: str = "en",
        target_lang: str = "zh-Hans",
    ):
        self.charmap = charmap or Charmap()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.glossary = glossary or Glossary(source_lang=source_lang, target_lang=target_lang)
        self.translator = translator or Translator(source_lang=source_lang, target_lang=target_lang)
        self.game = game
        self.needs_font_patch = is_cjk_language(target_lang)

    def translate_texts(
        self, texts_path: Path, output_path: Path, batch_size: int = 30,
        max_workers: int = 10,
    ) -> Path:
        """Translate extracted texts JSON with parallel workers."""
        data = json.loads(texts_path.read_text(encoding="utf-8"))
        data = convert_format(data)

        # Translate table entries (fast, glossary-based)
        for table in data["tables"]:
            self._translate_table(table)

        # Translate free texts in parallel batches
        free_texts = data["free_texts"]
        batches = [
            free_texts[i : i + batch_size]
            for i in range(0, len(free_texts), batch_size)
        ]
        total = len(batches)
        print(f"  共 {total} 批次，使用 {max_workers} 线程并行翻译")

        done_count = 0

        def process_batch(idx_batch):
            idx, batch = idx_batch
            self._translate_free_batch(batch)
            return idx

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_batch, (i, b)): i
                for i, b in enumerate(batches)
            }
            for future in as_completed(futures):
                done_count += 1
                idx = future.result()
                print(f"  [{done_count}/{total}] 批次 {idx + 1} 完成")

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
            # Check manual overrides for trainer classes (zh-Hans + firered only)
            if (
                self.target_lang == "zh-Hans"
                and self.game == "firered"
                and category == "trainer_classes"
                and original in _TRAINER_CLASS_OVERRIDES
            ):
                entry["translated"] = _TRAINER_CLASS_OVERRIDES[original]
                continue
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
                clean = _strip_llm_newlines(results[0])
                translated = restore(clean, codes)
                entry["translated"] = translated
            elif zh:
                # Had a glossary match but with bad chars, use it anyway
                entry["translated"] = zh
            else:
                # No translation available, keep original
                entry["translated"] = original

    def _translate_free_batch(self, batch: list[dict]):
        """Translate a batch of free text entries via LLM."""
        # Apply hardcoded overrides first (FireRed + zh-Hans only)
        remaining = []
        for entry in batch:
            entry_id = entry.get("id", "")
            if (
                self.target_lang == "zh-Hans"
                and self.game == "firered"
                and entry_id in _HARDCODED_TRANSLATIONS
            ):
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

        # Restore control codes and wrap text
        for i, entry in enumerate(remaining):
            # Strip literal newlines the LLM may have inserted for formatting.
            # At this point, semantic breaks are still encoded as {C0} etc.,
            # so any literal newlines are LLM formatting artifacts.
            clean = _strip_llm_newlines(results[i])
            translated = restore(clean, codes_list[i])
            entry["translated"] = wrap_text(translated)

    def _format_glossary(self, text: str) -> str:
        terms = self.glossary.get_context_terms(text)
        if not terms:
            return ""
        return "\n".join(f"  {en} = {zh}" for en, zh in terms.items())

    def build_rom(
        self,
        original_rom: Path,
        translations_path: Path,
        output_path: Path,
    ) -> Path:
        """Build final Chinese ROM."""
        # Auto-detect game from ROM header
        detected = detect_game(original_rom)
        if detected != "unknown":
            self.game = detected
            print(f"  Detected game: {self.game}")

        data = json.loads(translations_path.read_text(encoding="utf-8"))
        data = convert_format(data)

        writer = RomWriter(self.charmap, game=self.game)

        # 1. Load and expand ROM
        print("  Loading ROM...")
        rom = writer.load_rom(original_rom)
        rom = writer.expand_rom(rom)
        print(f"  ROM expanded to {len(rom) // (1024*1024)}MB")

        # 2. Apply font patch (CJK targets only)
        if self.needs_font_patch:
            print("  Applying font patch...")
            temp_rom = output_path.parent / "temp_fontpatch.gba"
            writer.save_rom(rom, temp_rom)
            apply_font_patch(temp_rom, temp_rom, game=self.game)
            rom = writer.load_rom(temp_rom)
            temp_rom.unlink(missing_ok=True)
            print("  Font patch applied")
        else:
            print("  Skipping font patch (Latin target language)")

        # 3. Collect all entries for injection
        all_entries = []
        for table in data["tables"]:
            for entry in table["entries"]:
                if "translated" in entry:
                    all_entries.append(entry)
        for entry in data["free_texts"]:
            if "translated" in entry:
                all_entries.append(entry)

        # 3b. Load manual entries (FireRed zh-Hans only)
        if self.game == "firered" and self.target_lang == "zh-Hans":
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
        # MeowthBridge hardcodes output to work/text.json, move if needed
        hardcoded = Path("work/text.json")
        if not output_path.exists() and hardcoded.exists():
            import shutil
            shutil.move(str(hardcoded), str(output_path))
        if not output_path.exists():
            raise RuntimeError(f"MeowthBridge did not produce {output_path}")
        # Post-process: replace HMA's raw FD escapes with named macros
        _postprocess_fd_macros(output_path)
        return output_path

    def run_full(
        self,
        rom_path: Path,
        output_dir: Path,
        work_dir: Path,
    ) -> Path:
        """Run the full translation pipeline: extract → translate → build."""
        # Auto-detect game if not explicitly set
        detected = detect_game(rom_path)
        if detected != "unknown":
            self.game = detected
            print(f"Detected game: {self.game}")
        else:
            print(f"Warning: could not detect game from ROM header, using: {self.game}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lang_suffix = self.target_lang.replace("-", "")

        texts_path = work_dir / "texts.json"
        translated_path = work_dir / "texts_translated.json"
        output_path = output_dir / f"{self.game}_{lang_suffix}_{timestamp}.gba"

        print("[1/3] Extracting texts from ROM...")
        self.extract_texts(rom_path, texts_path)

        print("[2/3] Translating texts...")
        self.translate_texts(texts_path, translated_path)

        print("[3/3] Building ROM...")
        self.build_rom(rom_path, translated_path, output_path)

        print(f"Complete: {output_path}")
        return output_path
