"""Main translation pipeline orchestration."""

import json
from datetime import datetime
from pathlib import Path

from .charmap import Charmap
from .control_codes import protect, restore
from .font_patch import apply_font_patch
from .glossary import Glossary
from .pcs_scanner import scan_and_merge
from .rom_writer import RomWriter
from .translator import Translator


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
            original = entry["original"]
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
        originals = [e["original"] for e in batch]

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
        for i, entry in enumerate(batch):
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

    def run_full(
        self,
        rom_path: Path,
        output_dir: Path,
        work_dir: Path,
    ) -> Path:
        """Run the full translation pipeline."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        texts_path = work_dir / "texts.json"
        translated_path = work_dir / "texts_translated.json"
        output_path = output_dir / f"firered_cn_{timestamp}.gba"

        print("[1/4] PCS scan — finding texts HMA missed...")
        scan_and_merge(rom_path, texts_path)

        print("[2/4] Translating texts...")
        self.translate_texts(texts_path, translated_path)

        print("[3/4] Building ROM...")
        self.build_rom(rom_path, translated_path, output_path)

        print(f"[4/4] Complete: {output_path}")
        return output_path
