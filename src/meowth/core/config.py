"""Unified configuration management for translation pipeline."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TranslationConfig:
    """Configuration for the translation pipeline.

    This class unifies configuration from CLI arguments, GUI forms,
    and meowth.toml files.
    """

    # Language settings
    source_lang: str = "en"
    target_lang: str = "zh-Hans"

    # LLM API settings
    provider: str | None = None
    api_base: str | None = None
    api_key_env: str | None = None
    api_key: str | None = None
    model: str | None = None

    # Translation settings
    batch_size: int = 30
    max_workers: int = 10

    # File paths
    rom_path: Path | None = None
    output_dir: Path = field(default_factory=lambda: Path("outputs"))
    work_dir: Path = field(default_factory=lambda: Path("work"))

    # Game detection (auto-detected if not specified)
    game: str = "firered"

    @classmethod
    def from_toml(cls, path: Path) -> "TranslationConfig":
        """Load configuration from a meowth.toml file.

        Args:
            path: Path to the meowth.toml file

        Returns:
            TranslationConfig instance with values from the TOML file
        """
        if not path.exists():
            return cls()

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        data = tomllib.loads(path.read_text(encoding="utf-8"))
        translation = data.get("translation", {})
        api = translation.get("api", {})

        return cls(
            source_lang=translation.get("source_language", "en"),
            target_lang=translation.get("target_language", "zh-Hans"),
            provider=translation.get("provider"),
            api_base=api.get("base_url"),
            api_key_env=api.get("key_env"),
            model=translation.get("model"),
            batch_size=translation.get("batch_size", 30),
            max_workers=translation.get("max_workers", 10),
        )

    @classmethod
    def from_cli_args(cls, **kwargs) -> "TranslationConfig":
        """Create configuration from CLI arguments.

        Args:
            **kwargs: Keyword arguments matching TranslationConfig fields

        Returns:
            TranslationConfig instance
        """
        # Filter out None values to use defaults
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        return cls(**filtered)

    def merge_with_toml(self, toml_path: Path) -> "TranslationConfig":
        """Merge this config with values from a TOML file.

        TOML values are used as defaults; existing non-None values take precedence.

        Args:
            toml_path: Path to the meowth.toml file

        Returns:
            New TranslationConfig with merged values
        """
        toml_config = self.from_toml(toml_path)

        # Use current values if set, otherwise fall back to TOML
        return TranslationConfig(
            source_lang=self.source_lang if self.source_lang != "en" else toml_config.source_lang,
            target_lang=self.target_lang if self.target_lang != "zh-Hans" else toml_config.target_lang,
            provider=self.provider or toml_config.provider,
            api_base=self.api_base or toml_config.api_base,
            api_key_env=self.api_key_env or toml_config.api_key_env,
            api_key=self.api_key,
            model=self.model or toml_config.model,
            batch_size=self.batch_size if self.batch_size != 30 else toml_config.batch_size,
            max_workers=self.max_workers if self.max_workers != 10 else toml_config.max_workers,
            rom_path=self.rom_path or toml_config.rom_path,
            output_dir=self.output_dir if self.output_dir != Path("outputs") else toml_config.output_dir,
            work_dir=self.work_dir if self.work_dir != Path("work") else toml_config.work_dir,
            game=self.game if self.game != "firered" else toml_config.game,
        )
