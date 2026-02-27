"""Main translation pipeline orchestration.

DEPRECATED: This module is kept for backward compatibility.
New code should use meowth.core.TranslationEngine instead.
"""

import warnings
from pathlib import Path

from .charmap import Charmap
from .core import TranslationCallbacks, TranslationConfig, TranslationEngine
from .core.engine import (
    TABLE_CATEGORIES,
    convert_format,
    detect_game,
    _HARDCODED_TRANSLATIONS,
    _TRAINER_CLASS_OVERRIDES,
)
from .glossary import Glossary
from .translator import Translator


class Pipeline:
    """Legacy Pipeline class for backward compatibility.

    DEPRECATED: Use meowth.core.TranslationEngine instead.
    This class wraps TranslationEngine to maintain backward compatibility.
    """

    def __init__(
        self,
        charmap: Charmap | None = None,
        glossary: Glossary | None = None,
        translator: Translator | None = None,
        game: str = "firered",
        source_lang: str = "en",
        target_lang: str = "zh-Hans",
        provider: str | None = None,
        api_base: str | None = None,
        api_key_env: str | None = None,
        model: str | None = None,
    ):
        """Initialize Pipeline (deprecated, use TranslationEngine)."""
        warnings.warn(
            "Pipeline is deprecated. Use meowth.core.TranslationEngine instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # Create config from parameters
        config = TranslationConfig(
            source_lang=source_lang,
            target_lang=target_lang,
            provider=provider,
            api_base=api_base,
            api_key_env=api_key_env,
            model=model,
            game=game,
        )

        # Create a simple callback that prints to stdout
        class PrintCallbacks(TranslationCallbacks):
            def on_log(self, level: str, message: str):
                print(message)

        # Create the engine
        self._engine = TranslationEngine(
            config=config,
            callbacks=PrintCallbacks(),
            charmap=charmap,
            glossary=glossary,
            translator=translator,
        )

        # Expose attributes for backward compatibility
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.charmap = self._engine.charmap
        self.glossary = self._engine.glossary
        self.translator = self._engine.translator
        self.game = game

    def translate_texts(
        self, texts_path: Path, output_path: Path, batch_size: int = 30,
        max_workers: int = 10,
    ) -> Path:
        """Translate extracted texts JSON with parallel workers."""
        self._engine.config.batch_size = batch_size
        self._engine.config.max_workers = max_workers
        return self._engine.translate_texts(texts_path, output_path)

    def build_rom(
        self,
        original_rom: Path,
        translations_path: Path,
        output_path: Path,
    ) -> Path:
        """Build final translated ROM."""
        return self._engine.build_rom(original_rom, translations_path, output_path)

    @staticmethod
    def find_meowth_bridge() -> Path:
        """Locate the MeowthBridge executable."""
        return TranslationEngine.find_meowth_bridge()

    @staticmethod
    def extract_texts(rom_path: Path, output_path: Path) -> Path:
        """Extract texts from ROM using MeowthBridge."""
        return TranslationEngine.extract_texts(rom_path, output_path)

    def run_full(
        self,
        rom_path: Path,
        output_dir: Path,
        work_dir: Path,
    ) -> Path:
        """Run the full translation pipeline: extract -> translate -> build."""
        self._engine.config.rom_path = rom_path
        self._engine.config.output_dir = output_dir
        self._engine.config.work_dir = work_dir
        return self._engine.run_full()
