"""Core translation engine - refactored from Pipeline with callback support."""

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..charmap import Charmap
from ..control_codes import protect, restore
from ..font_patch import apply_font_patch
from ..glossary import Glossary
from ..i18n import Messages
from ..korean_font import prepare_korean_font_patch
from ..korean_text import fit_korean_fixed_text
from ..languages import is_cjk_language
from ..pcs_codes import FD_MACROS
from ..pcs_scanner import is_real_text
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

FIXED_WIDTH_TABLE_CATEGORIES = {
    "pokemon_names", "move_names", "ability_names", "nature_names",
    "type_names", "item_names", "trainer_classes", "map_names",
    "habitat_names", "berry_names", "decoration_names", "pokedex_species",
    "trainer_names", "trade_nicknames", "trade_trainer_names",
    "menu_options", "menu_pc", "menu_pcoptions",
    "menu_pokemon", "menu_item_storage", "menu_pause",
    "menu_pokemon_options",
}

DESCRIPTION_LINE_WIDTH = 28
DESCRIPTION_WRAP_SETTINGS = {
    "move_descriptions": (16, 4),
    "ability_descriptions": (20, 2),
    "item_descriptions": (20, 2),
    "berry_descriptions": (20, 2),
    "decoration_descriptions": (20, 2),
    "pokedex_descriptions": (26, 4),
}
TRANSLATION_REUSE_SCHEMA = 2

# Table categories (routed through _translate_table instead of LLM free-text batches)
TABLE_CATEGORIES = FIXED_WIDTH_TABLE_CATEGORIES | {
    "battle_text",  # Emerald battle messages with \\00/\\0F/\\34 runtime variables
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

# Term overrides by original text (applied before LLM, all games, Chinese only)
_TERM_OVERRIDES: dict[str, str] = {
    "POKéDEX": "图鉴",
    "POKéMON": "宝可梦",
    "POKéNAV": "导航仪",
}


_KOREAN_OVERRIDES: dict[str, str] = {
    "Quick HMs": "빠른 비전",
    "Skip Cutscenes": "이벤트 생략",
    "Save Prompts": "저장 알림",
    "L-Button Mode": "L 버튼",
    "R-Button Mode": "R 버튼",
    "Sound Effects": "효과음",
    "Background Music": "배경음",
    "Bike&Surf Music": "자전거/파도타기",
    "Overworld Theme": "필드 음악",
    "Wild Theme": "야생 음악",
    "Trainer Theme": "트레이너 음악",
    "Battle Effects": "전투 연출",
    "Battle Difficulty": "전투 난이도",
    "Exp. Gain": "경험치",
    "Item Restrictions": "도구 제한",
    "Fast Messages": "빠른 메시지",
    "Type Icons": "타입 아이콘",
    "General Options": "일반 설정",
    "Audio Options": "사운드 설정",
    "Battle Options": "배틀 설정",
    "Auto-Run": "자동 달리기",
    "Reg Item 2": "등록 도구 2",
    "Dexnav Scan": "도감 탐색",
    "Mining Scan": "채굴 탐색",
    "View Party": "파티 보기",
    "View Items": "도구 보기",
    "Mission Log": "미션 기록",
    "Debug Menu": "디버그",
    "Puzzle Difficulty": "퍼즐 난이도",
    "Auto Item Sort": "도구 자동정렬",
    "By Amount": "수량순",
    "Semi-Shift": "반 교체",
    "Exp. Share": "경험치 공유",
    "Capped Exp. Share": "상한 경험치 공유",
    "4 Items Only": "도구 4개",
    "No Items": "도구 금지",
    "Enemy Trainer Only": "상대만",
    "Quick Run": "빠른 도망",
    "Team Preview": "상대 파티",
    "Frontier Only": "프런티어만",
    "Last Used Ball": "최근 볼",
    "After 1 Ball": "1회 후",
    "Always Best Ball": "최적 볼",
    "Nickname Offer": "별명 묻기",
    "Take Wild Item": "야생 도구 회수",
    "Audio Quality": "음질",
    "Low (Faster)": "낮음",
    "Medium (Default)": "보통",
    "High (Slower)": "높음",
    "Skip certain story cutscenes.": "일부 이벤트를 건너뜁니다.",
    "Receive prompts to save often.": "저장 알림을 자주 표시합니다.",
    "HMs can be used quicker in the field.": "필드에서 비전을 빠르게 씁니다.",
    "The difficulty of overworld puzzles.": "필드 퍼즐 난이도입니다.",
    "Auto sorts the Cube's Items sector.": "큐브 도구칸을 자동 정렬합니다.",
    "The frame style of certain text boxes.": "일부 창 테두리 모양입니다.",
    "The quality of all game audio.": "게임 전체 음질입니다.",
    "Which audio speakers play.": "사용할 스피커를 정합니다.",
    "Speakers may play differing audio.": "좌우 스피커를 다르게 씁니다.",
    "Both speakers play the same audio.": "양쪽 스피커를 같게 씁니다.",
    "Play sound effects and cries.": "효과음과 울음소리를 재생합니다.",
    "Play background music.": "배경 음악을 재생합니다.",
    "Play themes when biking and Surfing.": "자전거/파도타기 음악을 재생합니다.",
    "Override music for the overworld.": "필드 음악을 바꿉니다.",
    "Override music for wild battles.": "야생 배틀 음악을 바꿉니다.",
    "Override music for Trainer battles.": "트레이너 배틀 음악을 바꿉니다.",
    "View battle animations.": "배틀 연출을 표시합니다.",
    "Get free switch after a KO.": "기절 후 교체 기회를 줍니다.",
    "No free switch after a KO.": "기절 후 교체 기회가 없습니다.",
    "Get nameless free switch after a KO.": "기절 후 교체 안내를 줄입니다.",
    "The battle difficulty for all battles.": "모든 배틀의 난이도입니다.",
    "Button combination for fleeing quickly.": "빠른 도망 버튼 조합입니다.",
    "Exp. distribution after a KO.": "기절 후 경험치 배분입니다.",
    "Only the Pokémon sent out gain Exp.": "출전한 포켓몬만 경험치를 얻습니다.",
    "All Pokémon in the party gain Exp.": "파티 전원이 경험치를 얻습니다.",
    "Exp. Share with hard level caps.": "레벨 상한에 맞춰 경험치를 나눕니다.",
    "Rules for using items in Trainer battles.": "트레이너전 도구 사용 규칙입니다.",
    "Show prompt to view enemy team.": "상대 파티 확인을 묻습니다.",
    "Show prompt to use last Poke Ball.": "최근 사용한 볼을 묻습니다.",
    "Battle messages play with less delay.": "배틀 메시지를 빠르게 표시합니다.",
    "Pokémon types are shown when attacking.": "공격 시 타입 아이콘을 표시합니다.",
    "Offer to nickname a caught Pokémon.": "포획 후 별명을 물어봅니다.",
    "Put a caught Pokémon's item in the Cube.": "포획한 포켓몬의 도구를 큐브에 넣습니다.",
    "Save the selected settings.": "선택한 설정을 저장합니다.",
    "Save\r\nDiscard\\n\r\nCancel": "저장\n버리기\n취소",
    "[green]Save[black] or [red]discard[black] the selected settings?": "[green]저장[black] 또는 [red]버리기[black] 할까요?",
    "Oh!\r\nSilly me!\r\n\r\nHow can I expect you to find [green]Icicle\r\nCave[blue] if you don't know the way?\r\n\r\nThis [green]Town Map[blue] should aid you\r\nimmensely!": "아차!\n깜빡했구나!\n\n[green]얼음 동굴[blue]을 찾아가려면\n길을 알아야겠지?\n\n이 [green]타운 맵[blue]이\n큰 도움이 될 거야!",
    "Now, let's take a look at the\r\nTown Map, shall we?": "그럼 타운 맵을\n한번 확인해 볼까?",
}


def detect_game(rom_path: Path) -> str:
    """Detect game type from GBA ROM header (bytes 0xAC-0xAF)."""
    with open(rom_path, "rb") as f:
        f.seek(0xAC)
        code = f.read(4).decode("ascii", errors="replace")
    return _GAME_CODES.get(code, "unknown")


# Known font-rendering function addresses and expected THUMB prologue bytes for
# official binary ROMs. Decomp ROMs (pokeemerald, pokefirered, etc.) are
# recompiled from source, so these addresses contain completely different code.
_FONT_HOOK_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    "firered":   [(0x5790, b"\x70\xb5"), (0x5ed4, b"\xf0\xb5")],
    "leafgreen": [(0x5790, b"\x70\xb5"), (0x5ed4, b"\xf0\xb5")],
    "emerald":   [(0x57b4, b"\x70\xb5"), (0x5ed8, b"\xf0\xb5")],
}


def is_decomp_rom(rom_path: Path, game: str) -> bool:
    """Return True if this ROM is incompatible with the font patch.

    Checks whether the bytes at known font-rendering function addresses match
    the official binary ROM. Decomp ROMs (pokeemerald, pokefirered, etc.) are
    recompiled from source, so these addresses contain completely different code.
    Binary hacks applied on top of the original ROM preserve these bytes.
    """
    sigs = _FONT_HOOK_SIGNATURES.get(game)
    if sigs is None:
        return False  # unknown game, skip check
    with open(rom_path, "rb") as f:
        for offset, expected in sigs:
            f.seek(offset)
            if f.read(len(expected)) != expected:
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
        if cat in TABLE_CATEGORIES or "description" in cat:
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


def _is_placeholder_table_text(text: str) -> bool:
    """Return True for blank/dummy table values that should stay unchanged."""
    stripped = text.strip().strip('"')
    if not stripped:
        return True
    if stripped in {"-", "?", "??", "??????", "????????"}:
        return True
    if set(stripped) <= {"?", " ", "-"}:
        return True
    return False


def _has_translatable_text(protected: str) -> bool:
    """Return True if protected text still has content worth sending to LLM."""
    cleaned = re.sub(r"\{C\d+\}", "", protected)
    return sum(c.isalpha() for c in cleaned) >= 2


def _fit_korean_table_entry(entry: dict, text: str) -> str:
    category = entry.get("category", "")
    byte_length = int(entry.get("byte_length") or 0)
    if category in FIXED_WIDTH_TABLE_CATEGORIES and byte_length > 0:
        return fit_korean_fixed_text(text, byte_length, category)
    return text


def _is_description_entry(entry: dict) -> bool:
    return "description" in entry.get("category", "")


def _description_wrap_settings(entry: dict) -> tuple[int, int]:
    category = entry.get("category", "")
    return DESCRIPTION_WRAP_SETTINGS.get(category, (DESCRIPTION_LINE_WIDTH, 2))


def _korean_override(original: str) -> str | None:
    return _KOREAN_OVERRIDES.get(original.strip('"'))


def _format_korean_override(entry: dict, override: str) -> str:
    original = entry.get("original", "").strip('"')
    if original == "Save\r\nDiscard\\n\r\nCancel":
        return override
    return _postprocess_korean_entry_translation(entry, override)


def _postprocess_korean_entry_translation(entry: dict, text: str) -> str:
    text = _fit_korean_table_entry(entry, text)
    category = entry.get("category", "")
    if category in FIXED_WIDTH_TABLE_CATEGORIES:
        return text
    if _is_description_entry(entry):
        line_width, lines_per_box = _description_wrap_settings(entry)
        wrapped = wrap_text(
            text,
            line_width=line_width,
            lines_per_box=lines_per_box,
            target_lang="ko",
        )
        if category == "move_descriptions":
            return wrapped.replace("\\p", "\n").replace("\\n", "\n")
        return wrapped
    return wrap_text(text, target_lang="ko")


def _all_entries(data: dict) -> list[dict]:
    entries: list[dict] = []
    for table in data["tables"]:
        entries.extend(table["entries"])
    entries.extend(data["free_texts"])
    return entries


def _entry_reuse_keys(entry: dict) -> list[tuple]:
    original = entry.get("original", "").strip('"')
    return [
        (
            "table",
            entry.get("category", ""),
            entry.get("table_name", ""),
            entry.get("table_field", ""),
            entry.get("table_index", None),
            original,
        ),
        ("category_original", entry.get("category", ""), original),
    ]


def _is_reusable_translation(entry: dict, translated: str | None, target_lang: str) -> bool:
    if not translated:
        return False
    original = entry.get("original", "").strip('"')
    clean = translated.strip('"')
    if not clean:
        return False
    if target_lang == "ko":
        protected, _ = protect(original)
        return clean != original or not _has_translatable_text(protected)
    return clean != original


def _seed_existing_translations(data: dict, existing_path: Path, target_lang: str) -> int:
    if not existing_path.exists():
        return 0
    try:
        raw_existing = json.loads(existing_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if raw_existing.get("_meowth_translation_reuse_schema") != TRANSLATION_REUSE_SCHEMA:
        return 0
    existing = convert_format(raw_existing)

    by_key: dict[tuple, dict] = {}
    for old_entry in _all_entries(existing):
        for key in _entry_reuse_keys(old_entry):
            if key[1] != "":
                by_key.setdefault(key, old_entry)

    reused = 0
    for entry in _all_entries(data):
        if entry.get("translated"):
            continue
        for key in _entry_reuse_keys(entry):
            old_entry = by_key.get(key)
            if old_entry is None:
                continue
            translated = old_entry.get("translated")
            if not _is_reusable_translation(entry, translated, target_lang):
                continue
            if target_lang == "ko" and _is_description_entry(entry):
                translated = _postprocess_korean_entry_translation(entry, translated)
            entry["translated"] = translated
            reused += 1
            break
    return reused


def _normalize_korean_translations_for_build(data: dict) -> None:
    for entry in _all_entries(data):
        override = _korean_override(entry.get("original", ""))
        if override is not None:
            entry["translated"] = _format_korean_override(entry, override)
            continue
        translated = entry.get("translated")
        if translated and _is_description_entry(entry):
            entry["translated"] = _postprocess_korean_entry_translation(entry, translated)


def _dedupe_free_texts(entries: list[dict]) -> tuple[list[dict], list[list[dict]]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for entry in entries:
        key = (entry.get("category", ""), entry.get("original", "").strip('"'))
        groups.setdefault(key, []).append(entry)
    unique = [group[0] for group in groups.values()]
    duplicates = [group for group in groups.values() if len(group) > 1]
    return unique, duplicates


def _copy_duplicate_translations(duplicates: list[list[dict]]) -> None:
    for group in duplicates:
        translated = group[0].get("translated")
        if translated is None:
            continue
        for entry in group[1:]:
            entry["translated"] = translated


def _contains_hangul(text: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


def _assert_korean_translation_progress(data: dict) -> None:
    entries: list[dict] = []
    for table in data["tables"]:
        entries.extend(table["entries"])
    entries.extend(data["free_texts"])

    checked = 0
    hangul = 0
    unchanged = 0
    for entry in entries:
        original = entry.get("original", "").strip('"')
        translated = entry.get("translated", "").strip('"')
        if not translated:
            continue
        protected, _ = protect(original)
        if not _has_translatable_text(protected):
            continue
        checked += 1
        if translated == original:
            unchanged += 1
        if _contains_hangul(translated):
            hangul += 1

    if checked >= 5 and hangul == 0:
        raise RuntimeError(
            "Korean translation produced no Hangul text. The LLM/API appears "
            "to be returning English or failing; refusing to build an "
            "untranslated Korean ROM."
        )
    if checked >= 20 and unchanged == checked:
        raise RuntimeError(
            "Korean translation left every translatable entry unchanged. "
            "Check the API key, provider/model, and translation cache."
        )


def _hangul_translated_entries(entries: list[dict]) -> list[dict]:
    result = []
    for entry in entries:
        original = entry.get("original", "").strip('"')
        translated = entry.get("translated", "").strip('"')
        if translated and translated != original and _contains_hangul(translated):
            result.append(entry)
    return result


def _assert_korean_rom_injection(
    entries: list[dict],
    rom: bytearray,
    stats: dict,
    charmap: Charmap,
) -> None:
    hangul_entries = _hangul_translated_entries(entries)
    if not hangul_entries:
        raise RuntimeError(
            "Korean build has no Hangul translated entries to inject. "
            "Check the translation JSON before building."
        )

    written = stats.get("in_place", 0) + stats.get("relocated", 0)
    if written <= 0:
        raise RuntimeError(
            "Korean build injected zero translated entries. The ROM would stay "
            "English, so the build was stopped."
        )

    rom_bytes = bytes(rom)
    for entry in hangul_entries[:100]:
        translated = entry.get("translated", "").strip('"')
        encoded = charmap.encode(translated).rstrip(b"\xFF")
        if encoded and encoded in rom_bytes:
            return

    raise RuntimeError(
        "Korean translated text was generated, but no encoded Hangul text was "
        "found in the output ROM after injection. The writer path is not "
        "actually applying Korean text."
    )


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
            cache_dir=config.work_dir / "cache",
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
        reused = _seed_existing_translations(data, output_path, self.config.target_lang)
        if reused:
            self._log("info", f"Reused {reused:,} existing translations from {output_path}")

        # Translate table entries
        for table in data["tables"]:
            self._translate_table(table)

        # Translate only unique free-text entries. The entries are still the
        # original dict objects, so JSON output order remains stable; duplicate
        # translations are copied back after the worker batches complete.
        free_texts = data["free_texts"]
        unique_free_texts, duplicate_free_texts = _dedupe_free_texts(free_texts)
        free_texts_to_process = sorted(
            [entry for entry in unique_free_texts if not entry.get("translated")],
            key=lambda e: e.get("original", "").strip('"'),
        )
        batches = [
            free_texts_to_process[i : i + self.config.batch_size]
            for i in range(0, len(free_texts_to_process), self.config.batch_size)
        ]
        total = len(batches)
        self._log("info", Messages.BATCH_PROGRESS.format(
            total=total, workers=self.config.max_workers
        ))

        done_count = 0

        def process_batch(idx_batch):
            idx, batch = idx_batch
            self._translate_free_batch(batch)
            return idx, batch

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(process_batch, (i, b)): i
                for i, b in enumerate(batches)
            }
            for future in as_completed(futures):
                done_count += 1
                idx, batch = future.result()
                self._log("info", Messages.BATCH_COMPLETE.format(
                    current=done_count, total=total, batch_id=idx + 1
                ))
                sample = next((e for e in batch if e.get("translated")), None)
                if sample:
                    print(f"  e.g. {sample['original']!r} → {sample['translated']!r}")
                self.callbacks.on_progress("translate", done_count, total,
                    f"Batch {idx + 1} completed")

        _copy_duplicate_translations(duplicate_free_texts)
        if self.config.target_lang == "ko":
            _assert_korean_translation_progress(data)

        data["_meowth_translation_reuse_schema"] = TRANSLATION_REUSE_SCHEMA
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return output_path

    def _translate_table(self, table: dict):
        """Translate a table's entries using glossary lookup."""
        category = table["category"]
        needs_llm: list[dict] = []  # entries deferred to batch LLM call

        for entry in table["entries"]:
            if entry.get("translated"):
                continue
            original = entry["original"].strip('"')
            if _is_placeholder_table_text(original):
                entry["translated"] = original
                continue
            if self.config.target_lang == "ko":
                override = _korean_override(original)
                if override is not None:
                    entry["translated"] = _format_korean_override(entry, override)
                    continue
            # Check term overrides (all games, Chinese only)
            if self.config.target_lang == "zh-Hans" and original in _TERM_OVERRIDES:
                entry["translated"] = _TERM_OVERRIDES[original]
                continue
            # Check manual overrides
            if (category == "trainer_classes" and
                self.config.target_lang == "zh-Hans" and
                original in _TRAINER_CLASS_OVERRIDES):
                entry["translated"] = _TRAINER_CLASS_OVERRIDES[original]
                continue
            # Try glossary lookup
            zh = self.glossary.lookup(original)
            if zh and self.config.target_lang == "ko":
                entry["translated"] = _postprocess_korean_entry_translation(entry, zh)
                continue
            elif zh:
                ok, bad = self.charmap.can_encode(zh)
                if ok:
                    entry["translated"] = zh
                    continue
            # Descriptions, map names without glossary match, and battle text:
            # defer to batch LLM call instead of one-by-one to avoid 500+ API calls
            if (
                self.config.target_lang == "ko"
                or "description" in category
                or (category == "map_names" and not zh)
                or category == "battle_text"
            ):
                needs_llm.append(entry)
            elif zh:
                entry["translated"] = zh
            else:
                entry["translated"] = original

        # Batch translate all deferred LLM entries
        if needs_llm:
            self._translate_table_llm_batch(needs_llm)

        # Inject map_names and pokemon_names into glossary for consistency
        # (so free-text LLM calls can reference these translations)
        if category in ("map_names", "pokemon_names"):
            for entry in table["entries"]:
                original = entry["original"].strip('"')
                translated = entry.get("translated", "")
                if translated and translated != original:
                    self.glossary.add_term(original, translated, "dynamic")

    def _translate_table_llm_batch(self, entries: list[dict]):
        """Batch LLM translate table entries (descriptions, map names, battle text).

        Filters out entries that are pure control codes (nothing for LLM to
        translate), then sends the rest in batches of batch_size, same as
        free-text processing.
        """
        # Separate: entries with real text vs pure control-code entries
        to_translate: list[tuple[dict, str, list]] = []  # (entry, protected, codes)
        for entry in entries:
            original = entry["original"].strip('"')
            protected, codes = protect(original)
            # Count actual alphabetic letters after stripping {C0}-style placeholders
            if _has_translatable_text(protected):
                to_translate.append((entry, protected, codes))
            else:
                # Pure control codes – keep original, nothing to translate
                entry["translated"] = original

        if not to_translate:
            return

        grouped: dict[str, list[tuple[dict, list]]] = {}
        for entry, protected, codes in to_translate:
            grouped.setdefault(protected, []).append((entry, codes))

        # Batch translate unique protected strings in groups of batch_size.
        batch_size = self.config.batch_size
        protected_all = list(grouped)
        for i in range(0, len(protected_all), batch_size):
            protected_list = protected_all[i : i + batch_size]
            all_text = " ".join(
                grouped[protected][0][0]["original"] for protected in protected_list
            )
            glossary_ctx = self._format_glossary(all_text)

            try:
                results = self.translator.translate_batch(protected_list, glossary_ctx)
            except Exception as e:
                if self.config.target_lang == "ko":
                    raise RuntimeError(f"Korean table translation failed: {e}") from e
                print(f"[Table batch LLM failed: {e}, keeping originals]")
                for protected in protected_list:
                    for entry, _ in grouped[protected]:
                        entry["translated"] = entry["original"].strip('"')
                continue

            for protected, result in zip(protected_list, results):
                clean = _strip_llm_newlines(result)
                for entry, codes in grouped[protected]:
                    translated = restore(clean, codes)
                    if self.config.target_lang == "ko":
                        translated = _postprocess_korean_entry_translation(entry, translated)
                    entry["translated"] = translated

    def _translate_free_batch(self, batch: list[dict]):
        """Translate a batch of free text entries via LLM."""
        # Apply hardcoded overrides
        remaining = []
        for entry in batch:
            if entry.get("translated"):
                continue
            entry_id = entry.get("id", "")
            original = entry.get("original", "").strip('"')
            if _is_placeholder_table_text(original):
                entry["translated"] = original
                continue
            if entry.get("category") == "scripts" and not is_real_text(original):
                entry["translated"] = original
                continue
            if self.config.target_lang == "ko":
                override = _korean_override(original)
                if override is not None:
                    entry["translated"] = _format_korean_override(entry, override)
                    continue
            term = self.glossary.lookup(original)
            if term and self.config.target_lang == "ko":
                entry["translated"] = _postprocess_korean_entry_translation(entry, term)
                continue
            if (self.config.target_lang == "zh-Hans" and
                original in _TERM_OVERRIDES):
                entry["translated"] = _TERM_OVERRIDES[original]
            elif (self.config.game == "firered" and
                self.config.target_lang == "zh-Hans" and
                entry_id in _HARDCODED_TRANSLATIONS):
                entry["translated"] = _HARDCODED_TRANSLATIONS[entry_id]
            else:
                remaining.append(entry)

        if not remaining:
            return

        # Protect control codes and collapse duplicates within the batch.
        grouped: dict[str, list[tuple[dict, list]]] = {}
        originals_by_key: dict[str, str] = {}
        for entry in remaining:
            original = entry["original"]
            protected, codes = protect(original)
            if not _has_translatable_text(protected):
                entry["translated"] = original
                continue
            grouped.setdefault(protected, []).append((entry, codes))
            originals_by_key.setdefault(protected, original)

        if not grouped:
            return

        protected_list = list(grouped)

        # Build glossary context
        all_text = " ".join(originals_by_key.values())
        glossary_ctx = self._format_glossary(all_text)

        # Translate
        try:
            results = self.translator.translate_batch(protected_list, glossary_ctx)
        except Exception as e:
            if self.config.target_lang == "ko":
                raise RuntimeError(f"Korean text translation failed: {e}") from e
            print(f"[Batch failed after retries: {e}, keeping originals]")
            for entry in remaining:
                entry["translated"] = entry["original"]
            return

        # Restore and wrap
        for protected, result in zip(protected_list, results):
            clean = _strip_llm_newlines(result)
            for entry, codes in grouped[protected]:
                translated = restore(clean, codes)
                if self.config.target_lang == "ko":
                    translated = _postprocess_korean_entry_translation(entry, translated)
                    entry["translated"] = translated
                    continue
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

        data = json.loads(translations_path.read_text(encoding="utf-8"))
        data = convert_format(data)
        if self.config.target_lang == "ko":
            _normalize_korean_translations_for_build(data)
            _assert_korean_translation_progress(data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)

        # Collect all entries before patching so Korean builds can subset fonts
        # to exactly the glyphs that may be injected into the ROM.
        all_entries = []
        for table in data["tables"]:
            for entry in table["entries"]:
                if "translated" in entry:
                    all_entries.append(entry)
        for entry in data["free_texts"]:
            if "translated" in entry:
                all_entries.append(entry)

        # Chinese-only manual entries must not leak into Korean builds.
        if self.config.game == "firered" and self.config.target_lang == "zh-Hans":
            manual_path = Path(__file__).parent.parent / "manual_entries.json"
            if manual_path.exists():
                manual = json.loads(manual_path.read_text(encoding="utf-8"))
                all_entries.extend(manual)
                self._log("info", Messages.ADDED_MANUAL_ENTRIES.format(count=len(manual)))

        patch_root = None
        if self.config.target_lang == "ko":
            if not self.config.korean_font_zip:
                raise RuntimeError(
                    "Korean builds require Galmuri-v2.40.3.zip. "
                    "Pass --korean-font-zip or set MEOWTH_KOREAN_FONT_ZIP."
                )
            patch_root, charmap_path, font_result = prepare_korean_font_patch(
                self.config.korean_font_zip,
                self.config.work_dir,
                self.config.game,
                entries=all_entries,
                rom_path=original_rom,
            )
            self.charmap = Charmap(charmap_path=charmap_path, target_lang="ko")
            self._log(
                "info",
                f"Korean font subset generated: {font_result.glyph_count}/"
                f"{font_result.capacity} glyphs",
            )

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
            if patch_root is not None:
                apply_font_patch(temp_rom, temp_rom, game=self.config.game, patch_root=patch_root)
            else:
                apply_font_patch(temp_rom, temp_rom, game=self.config.game)
            rom = writer.load_rom(temp_rom)
            temp_rom.unlink(missing_ok=True)
            self._log("info", Messages.FONT_PATCH_APPLIED)
        else:
            self._log("info", Messages.SKIPPING_FONT_PATCH.format(lang=self.config.target_lang))

        # Inject texts
        self._log("info", Messages.INJECTING_TEXTS.format(count=len(all_entries)))
        rom, stats = writer.inject_texts(rom, all_entries)
        if self.config.target_lang == "ko" and stats.get("errors", 0):
            raise RuntimeError(
                f"Korean ROM injection failed for {stats['errors']} entries. "
                "The build was stopped instead of outputting a partially "
                "English ROM."
            )
        if self.config.target_lang == "ko" and (
            stats.get("skipped_fixed_too_long", 0)
            or stats.get("skipped_no_address", 0)
            or stats.get("skipped_unsafe", 0)
        ):
            raise RuntimeError(
                "Korean ROM injection skipped translatable entries "
                f"(fixed-too-long={stats.get('skipped_fixed_too_long', 0)}, "
                f"no-address={stats.get('skipped_no_address', 0)}, "
                f"unsafe={stats.get('skipped_unsafe', 0)}). "
                "The build was stopped instead of outputting a partially "
                "English ROM."
            )
        if self.config.target_lang == "ko":
            _assert_korean_rom_injection(all_entries, rom, stats, self.charmap)
            if stats.get("compacted", 0):
                self._log(
                    "info",
                    "Korean text compacted to fit ROM space: "
                    f"{stats.get('compacted', 0)} entries, "
                    f"{stats.get('compacted_saved', 0):,} bytes saved",
                )
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
        import shutil as _shutil
        from ..resource_path import get_resource_path

        exe = TranslationEngine.find_meowth_bridge()
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rom_abs = rom_path.resolve()

        # Use output_path.parent (the work dir) as MeowthBridge's CWD.
        # This is always a writable directory (e.g. ~/Library/Caches/Meowth/work).
        cwd = output_path.parent

        # MeowthBridge (via HMA) needs resources/ to exist in its CWD.
        # Find the actual resources directory and symlink/copy it into cwd.
        resources_src = get_resource_path("resources")
        if not (resources_src / "hma.py").exists():
            dev_resources = get_resource_path("HexManiacAdvance/src/HexManiac.Core/Models/Code")
            if (dev_resources / "hma.py").exists():
                resources_src = dev_resources
        resources_dst = cwd / "resources"
        if resources_dst.exists() and not (resources_dst / "hma.py").exists():
            if resources_dst.is_symlink() or resources_dst.is_file():
                resources_dst.unlink()
            else:
                _shutil.rmtree(str(resources_dst))
        if resources_src.exists() and not resources_dst.exists():
            try:
                os.symlink(resources_src, resources_dst)
            except (OSError, NotImplementedError):
                _shutil.copytree(str(resources_src), str(resources_dst))
        resources_dst.mkdir(exist_ok=True)

        result = subprocess.run(
            [str(exe), "extract", str(rom_abs)],
            capture_output=True, text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd),
        )
        if result.returncode != 0:
            raise RuntimeError(
                Messages.MEOWTH_BRIDGE_FAILED.format(
                    code=result.returncode, stderr=result.stderr
                )
            )

        # MeowthBridge writes output to <cwd>/work/text.json
        hardcoded = cwd / "work" / "text.json"
        if hardcoded.exists():
            _shutil.move(str(hardcoded), str(output_path))
        if not output_path.exists():
            raise RuntimeError(Messages.MEOWTH_BRIDGE_NO_OUTPUT.format(path=output_path))

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

        # Compatibility check 1: reject Ruby/Sapphire
        if self.config.game in ("ruby", "sapphire"):
            raise RuntimeError(Messages.ROM_UNSUPPORTED_GAME.format(game=self.config.game))

        # Compatibility check 2: reject decomp hacks when targeting CJK
        from ..languages import is_cjk_language
        if is_cjk_language(self.config.target_lang) and is_decomp_rom(rom_path, self.config.game):
            with open(rom_path, "rb") as _f:
                _f.seek(0xAC)
                _raw_code = _f.read(4).decode("ascii", errors="replace")
            raise RuntimeError(Messages.ROM_DECOMP_HACK.format(code=_raw_code))

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
