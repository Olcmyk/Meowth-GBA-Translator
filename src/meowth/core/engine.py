"""Core translation engine - refactored from Pipeline with callback support."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..charmap import Charmap
from ..control_codes import protect, restore
from ..font_patch import apply_font_patch
from ..glossary import Glossary
from ..i18n import Messages
from ..languages import is_cjk_language
from ..pcs_codes import FD_MACROS
from ..rom_writer import RomWriter
from ..text_wrap import wrap_text
from ..translator import Translator
from .callbacks import TranslationCallbacks
from .config import TranslationConfig

# Game detection from ROM header
_GAME_CODES: dict[str, str] = {
    "BPRE": "firered",
    "BPGE": "leafgreen",
    "BPEE": "emerald",
    "AXVE": "ruby",
    "AXPE": "sapphire",
}

# Table categories
TABLE_CATEGORIES = {
    "pokemon_names", "move_names", "ability_names", "nature_names",
    "type_names", "item_names", "trainer_classes", "map_names",
}

# Hardcoded translations (FireRed + Chinese only)
_HARDCODED_TRANSLATIONS: dict[str, str] = {
    "scr_02219": (
        "你将成为主角，\n探索宝可梦的世界！"
        "\n\n通过与人们交谈并解开谜题，\n新的道路将为你敞开。"
        "\n\n与你出色的宝可梦一起，\n朝着目标努力吧！"
    ),
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

# Manual trainer class translations
_TRAINER_CLASS_OVERRIDES: dict[str, str] = {
    "RIVAL": "劲敌",
}

# Menu item translations (shortened to fit byte limits)
# Note: With automatic pointer detection, most items can now use full translations
_MENU_ITEM_OVERRIDES: dict[str, str] = {
    # Reserved for future manual overrides if needed
}


def detect_game(rom_path: Path) -> str:
    """Detect game type from GBA ROM header (bytes 0xAC-0xAF)."""
    with open(rom_path, "rb") as f:
        f.seek(0xAC)
        code = f.read(4).decode("ascii", errors="replace")
    return _GAME_CODES.get(code, "unknown")


def is_decomp_rom(rom_path: Path) -> bool:
    """Detect if ROM is a decomp (source-built) ROM rather than a binary hack.

    Decomp ROMs typically have:
    1. Different internal structure (no traditional free space patterns)
    2. Modified build info strings
    3. Different code organization

    This checks for common decomp indicators:
    - Presence of specific build strings (e.g., "pokeemerald", "pokefirered")
    - Unusual ROM size (decomp ROMs often have non-standard sizes)
    - Modified game title in header
    """
    with open(rom_path, "rb") as f:
        # Read game title (0xA0-0xAB)
        f.seek(0xA0)
        title = f.read(12).decode("ascii", errors="replace")

        # Read game code (0xAC-0xAF)
        game_code = f.read(4).decode("ascii", errors="replace")

        # Get ROM size
        f.seek(0, 2)  # Seek to end
        rom_size = f.tell()

        # Read a sample of ROM data to check for decomp strings
        f.seek(0)
        rom_data = f.read(min(rom_size, 2 * 1024 * 1024))  # Read first 2MB

    # Check for decomp indicators
    decomp_indicators = [
        b"pokeemerald",
        b"pokefirered",
        b"pokeleafgreen",
        b"pokeruby",
        b"pokesapphire",
        b"pret/",  # pret organization marker
        b"expansion",  # pokeemerald-expansion
    ]

    # Check if any decomp strings are present
    for indicator in decomp_indicators:
        if indicator in rom_data:
            return True

    # Check for non-standard ROM sizes (decomp ROMs often aren't exact power of 2)
    # Standard GBA ROM sizes: 8MB, 16MB, 32MB
    standard_sizes = {8 * 1024 * 1024, 16 * 1024 * 1024, 32 * 1024 * 1024}
    if rom_size not in standard_sizes:
        # Check if it's close to a standard size (within 1MB)
        is_close_to_standard = any(abs(rom_size - size) < 1024 * 1024 for size in standard_sizes)
        if not is_close_to_standard:
            return True

    # Check for modified game title (decomp ROMs often have custom titles)
    # Standard titles start with "POKEMON"
    if game_code in _GAME_CODES and not title.upper().startswith("POKEMON"):
        return True

    return False



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


def _strip_llm_newlines(text: str) -> str:
    """Remove literal newlines inserted by the LLM for formatting."""
    _PARA = "\x00PARA\x00"
    text = text.replace("\n\n", _PARA)
    text = text.replace("\n", "")
    text = text.replace(_PARA, "\n\n")
    return text


def _postprocess_fd_macros(json_path: Path):
    """Replace HMA's raw FD escape sequences with named macros."""
    _HMA_KNOWN = {0x01, 0x02, 0x03, 0x04, 0x06}
    replacements = {}
    for code, name in FD_MACROS.items():
        if code not in _HMA_KNOWN:
            replacements[f"\\\\\\\\{code:02X}"] = name
    if not replacements:
        return
    text = json_path.read_text(encoding="utf-8")
    for raw, macro in replacements.items():
        text = text.replace(raw, macro)
    json_path.write_text(text, encoding="utf-8")


class TranslationEngine:
    """Core translation engine with callback support.

    This is the refactored version of Pipeline that uses callbacks
    instead of print() statements, enabling both CLI and GUI interfaces.
    """

    def __init__(
        self,
        config: TranslationConfig,
        callbacks: TranslationCallbacks | None = None,
        charmap: Charmap | None = None,
        glossary: Glossary | None = None,
        translator: Translator | None = None,
    ):
        """Initialize the translation engine.

        Args:
            config: Translation configuration
            callbacks: Callback handler for progress and logging
            charmap: Character mapping (auto-created if None)
            glossary: Glossary for term translation (auto-created if None)
            translator: LLM translator (auto-created if None)
        """
        self.config = config
        self.callbacks = callbacks or TranslationCallbacks()

        self.charmap = charmap or Charmap(target_lang=config.target_lang)
        self.glossary = glossary or Glossary(
            source_lang=config.source_lang,
            target_lang=config.target_lang
        )
        self.translator = translator or Translator(
            source_lang=config.source_lang,
            target_lang=config.target_lang,
            provider=config.provider,
            base_url=config.api_base,
            api_key=config.api_key,
            api_key_env=config.api_key_env,
            model=config.model,
        )

    def _log(self, level: str, message: str):
        """Internal helper to send log messages via callbacks."""
        self.callbacks.on_log(level, message)

    def translate_texts(
        self, texts_path: Path, output_path: Path
    ) -> Path:
        """Translate extracted texts JSON with parallel workers."""
        data = json.loads(texts_path.read_text(encoding="utf-8"))
        data = convert_format(data)

        # Translate table entries
        for table in data["tables"]:
            self._translate_table(table)

        # Translate free texts in parallel batches
        free_texts = data["free_texts"]
        batches = [
            free_texts[i : i + self.config.batch_size]
            for i in range(0, len(free_texts), self.config.batch_size)
        ]
        total = len(batches)
        self._log("info", Messages.BATCH_PROGRESS.format(
            total=total, workers=self.config.max_workers
        ))

        done_count = 0

        def process_batch(idx_batch):
            idx, batch = idx_batch
            self._translate_free_batch(batch)
            return idx

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(process_batch, (i, b)): i
                for i, b in enumerate(batches)
            }
            for future in as_completed(futures):
                done_count += 1
                idx = future.result()
                self._log("info", Messages.BATCH_COMPLETE.format(
                    current=done_count, total=total, batch_id=idx + 1
                ))
                self.callbacks.on_progress("translate", done_count, total,
                    f"Batch {idx + 1} completed")

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
            # Check manual overrides
            if (category == "trainer_classes" and
                self.config.target_lang == "zh-Hans" and
                original in _TRAINER_CLASS_OVERRIDES):
                entry["translated"] = _TRAINER_CLASS_OVERRIDES[original]
                continue
            # Try glossary lookup
            zh = self.glossary.lookup(original)
            if zh:
                ok, bad = self.charmap.can_encode(zh)
                if ok:
                    entry["translated"] = zh
                    continue
            # For descriptions, use LLM
            if "description" in category:
                protected, codes = protect(original)
                glossary_ctx = self._format_glossary(original)
                results = self.translator.translate_batch([protected], glossary_ctx)
                clean = _strip_llm_newlines(results[0])
                translated = restore(clean, codes)
                entry["translated"] = translated
            elif zh:
                entry["translated"] = zh
            else:
                entry["translated"] = original

    def _translate_free_batch(self, batch: list[dict]):
        """Translate a batch of free text entries via LLM."""
        # Apply hardcoded overrides
        remaining = []
        for entry in batch:
            entry_id = entry.get("id", "")
            if (self.config.game == "firered" and
                self.config.target_lang == "zh-Hans" and
                entry_id in _HARDCODED_TRANSLATIONS):
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

        # Build glossary context
        all_text = " ".join(originals)
        glossary_ctx = self._format_glossary(all_text)

        # Translate
        results = self.translator.translate_batch(protected_list, glossary_ctx)

        # Restore and wrap
        for i, entry in enumerate(remaining):
            clean = _strip_llm_newlines(results[i])
            translated = restore(clean, codes_list[i])
            entry["translated"] = wrap_text(translated, target_lang=self.config.target_lang)

    def _format_glossary(self, text: str) -> str:
        terms = self.glossary.get_context_terms(text)
        if not terms:
            return ""
        return "\n".join(f"  {src} = {tgt}" for src, tgt in terms.items())

    def build_rom(
        self,
        original_rom: Path,
        translations_path: Path,
        output_path: Path,
    ) -> Path:
        """Build final translated ROM."""
        # Auto-detect game
        detected = detect_game(original_rom)
        if detected != "unknown":
            self.config.game = detected
            self._log("info", Messages.DETECTED_GAME.format(game=self.config.game))

        # Check for decomp ROM when translating to CJK languages (requires font injection)
        if is_cjk_language(self.config.target_lang):
            if is_decomp_rom(original_rom):
                error_msg = (
                    f"错误：检测到这是一个 decomp ROM（源码编译版本），而非 binary ROM。\n"
                    f"Decomp ROM 无法使用字库注入功能，因此无法翻译成中文。\n\n"
                    f"如果您想翻译 decomp ROM，请：\n"
                    f"1. 直接修改源代码中的文本\n"
                    f"2. 在源码中添加中文字库支持\n"
                    f"3. 重新编译 ROM\n\n"
                    f"本工具仅支持 binary ROM（原版或基于原版的二进制改版）。"
                )
                self._log("error", error_msg)
                raise RuntimeError(error_msg)

        data = json.loads(translations_path.read_text(encoding="utf-8"))
        data = convert_format(data)

        writer = RomWriter(self.charmap, game=self.config.game,
                          target_lang=self.config.target_lang)

        # Load and expand ROM
        self._log("info", Messages.LOADING_ROM)
        rom = writer.load_rom(original_rom)
        rom = writer.expand_rom(rom)
        self._log("info", Messages.ROM_EXPANDED.format(size=len(rom) // (1024*1024)))

        # Apply font patch for CJK languages
        if is_cjk_language(self.config.target_lang):
            self._log("info", Messages.APPLYING_FONT_PATCH)
            temp_rom = output_path.parent / "temp_fontpatch.gba"
            writer.save_rom(rom, temp_rom)
            apply_font_patch(temp_rom, temp_rom, game=self.config.game)
            rom = writer.load_rom(temp_rom)
            temp_rom.unlink(missing_ok=True)
            self._log("info", Messages.FONT_PATCH_APPLIED)
        else:
            self._log("info", Messages.SKIPPING_FONT_PATCH.format(lang=self.config.target_lang))

        # Collect all entries
        all_entries = []
        for table in data["tables"]:
            for entry in table["entries"]:
                if "translated" in entry:
                    all_entries.append(entry)
        for entry in data["free_texts"]:
            if "translated" in entry:
                all_entries.append(entry)

        # Load manual entries (FireRed-specific)
        if self.config.game == "firered":
            manual_path = Path(__file__).parent.parent / "manual_entries.json"
            if manual_path.exists():
                manual = json.loads(manual_path.read_text(encoding="utf-8"))
                all_entries.extend(manual)
                self._log("info", Messages.ADDED_MANUAL_ENTRIES.format(count=len(manual)))

        # Inject texts
        self._log("info", Messages.INJECTING_TEXTS.format(count=len(all_entries)))
        rom, stats = writer.inject_texts(rom, all_entries)
        self._log("info", Messages.INJECTION_STATS.format(
            in_place=stats['in_place'],
            relocated=stats['relocated'],
            skipped=stats['skipped'],
            partial_ptr=stats.get('skipped_partial_ptrs', 0),
            unsafe_ptr=stats.get('unsafe_ptrs', 0)
        ))

        # Save
        writer.save_rom(rom, output_path)
        self._log("info", Messages.SAVED_ROM.format(path=output_path))
        return output_path

    @staticmethod
    def find_meowth_bridge() -> Path:
        """Locate the MeowthBridge executable."""
        from ..binaries import find_meowth_bridge
        return find_meowth_bridge()

    @staticmethod
    def extract_texts(rom_path: Path, output_path: Path) -> Path:
        """Extract texts from ROM using MeowthBridge."""
        import os
        exe = TranslationEngine.find_meowth_bridge()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine working directory for MeowthBridge
        # - In packaged mode: MeowthBridge directory has bundled resources/
        # - In dev mode: project root has resources/
        original_cwd = Path.cwd()
        bridge_dir = exe.parent

        # Check if resources exists in bridge directory (packaged mode)
        if (bridge_dir / "resources").exists():
            work_dir = bridge_dir
        else:
            # Dev mode: use project root where resources/ exists
            # Find project root by looking for HexManiacAdvance submodule
            project_root = bridge_dir
            while project_root.parent != project_root:
                if (project_root / "HexManiacAdvance").exists():
                    break
                project_root = project_root.parent
            work_dir = project_root

        os.chdir(work_dir)

        try:
            # Use absolute paths for ROM and output since we changed directory
            rom_abs = rom_path.resolve()
            output_abs = output_path.resolve()

            result = subprocess.run(
                [str(exe), "extract", str(rom_abs)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    Messages.MEOWTH_BRIDGE_FAILED.format(
                        code=result.returncode, stderr=result.stderr
                    )
                )
            # MeowthBridge outputs to work/text.json in its working directory
            hardcoded = Path("work/text.json")
            if hardcoded.exists():
                import shutil
                shutil.move(str(hardcoded), str(output_abs))
            if not output_abs.exists():
                raise RuntimeError(Messages.MEOWTH_BRIDGE_NO_OUTPUT.format(path=output_abs))
        finally:
            os.chdir(original_cwd)

        _postprocess_fd_macros(output_path)
        return output_path

    def run_full(
        self,
        rom_path: Path | None = None,
        output_dir: Path | None = None,
        work_dir: Path | None = None,
    ) -> Path:
        """Run the full translation pipeline: extract -> translate -> build."""
        # Use config values if not provided
        rom_path = rom_path or self.config.rom_path
        output_dir = output_dir or self.config.output_dir
        work_dir = work_dir or self.config.work_dir

        if rom_path is None:
            raise ValueError("rom_path must be provided")

        # Convert all paths to absolute to avoid issues with working directory changes
        rom_path = Path(rom_path).resolve()
        output_dir = Path(output_dir).resolve()
        work_dir = Path(work_dir).resolve()

        # Auto-detect game
        detected = detect_game(rom_path)
        if detected != "unknown":
            self.config.game = detected
            self._log("info", Messages.DETECTED_GAME.format(game=self.config.game))
        else:
            self._log("warning", Messages.GAME_DETECTION_FAILED.format(game=self.config.game))

        # Check for decomp ROM when translating to CJK languages (requires font injection)
        if is_cjk_language(self.config.target_lang):
            if is_decomp_rom(rom_path):
                error_msg = (
                    f"错误：检测到这是一个 decomp ROM（源码编译版本），而非 binary ROM。\n"
                    f"Decomp ROM 无法使用字库注入功能，因此无法翻译成中文。\n\n"
                    f"如果您想翻译 decomp ROM，请：\n"
                    f"1. 直接修改源代码中的文本\n"
                    f"2. 在源码中添加中文字库支持\n"
                    f"3. 重新编译 ROM\n\n"
                    f"本工具仅支持 binary ROM（原版或基于原版的二进制改版）。"
                )
                self._log("error", error_msg)
                raise RuntimeError(error_msg)

        # Generate output filename
        original_name = rom_path.stem
        lang_code = self.config.target_lang.split("-")[0]

        texts_path = work_dir / "texts.json"
        translated_path = work_dir / "texts_translated.json"
        output_path = output_dir / f"{original_name}_{lang_code}.gba"

        # Stage 1: Extract
        self.callbacks.on_stage_change("extract", "started")
        self._log("info", Messages.STAGE_EXTRACT)
        self.extract_texts(rom_path, texts_path)
        self.callbacks.on_stage_change("extract", "completed")

        # Stage 2: Translate
        self.callbacks.on_stage_change("translate", "started")
        self._log("info", Messages.STAGE_TRANSLATE)
        self.translate_texts(texts_path, translated_path)
        self.callbacks.on_stage_change("translate", "completed")

        # Stage 3: Build
        self.callbacks.on_stage_change("build", "started")
        self._log("info", Messages.STAGE_BUILD)
        self.build_rom(rom_path, translated_path, output_path)
        self.callbacks.on_stage_change("build", "completed")

        self._log("info", Messages.COMPLETE.format(output=output_path))
        return output_path
