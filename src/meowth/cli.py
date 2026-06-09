"""Meowth CLI - GBA Pokemon translation tool."""

from pathlib import Path
import json

import click

from .core import TranslationCallbacks, TranslationConfig, TranslationEngine
from .core.config import DEFAULT_BATCH_SIZE, DEFAULT_MAX_WORKERS
from .korean_font import default_korean_font_zip, generate_korean_font_assets, render_font_preview
from .languages import validate_language
from .pipeline import Pipeline
from .translator import PROVIDER_PRESETS


def _load_env():
    """Load .env file if present."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                import os
                os.environ.setdefault(key.strip(), val.strip())


def _load_config() -> dict:
    """Load meowth.toml config if present."""
    config_path = Path(__file__).parent.parent.parent / "meowth.toml"
    if not config_path.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    return tomllib.loads(config_path.read_text(encoding="utf-8"))


def _provider_kwargs(provider, api_base, api_key_env, model) -> dict:
    """Build provider kwargs from CLI options, falling back to meowth.toml."""
    cfg = _load_config()
    t = cfg.get("translation", {})
    api_cfg = t.get("api", {})

    return {
        "provider": provider or t.get("provider"),
        "api_base": api_base or api_cfg.get("base_url"),
        "api_key_env": api_key_env or api_cfg.get("key_env"),
        "model": model or t.get("model"),
    }


def _get_language(cli_value, cli_default, config_key) -> str:
    """Get language from CLI or config, preferring config if CLI is default."""
    cfg = _load_config()
    t = cfg.get("translation", {})
    # If CLI value is not the default, use it; otherwise use config
    if cli_value != cli_default:
        return cli_value
    return t.get(config_key, cli_default)


# Shared CLI options for LLM provider configuration
_provider_options = [
    click.option("--provider", default=None, type=click.Choice(sorted(PROVIDER_PRESETS.keys()), case_sensitive=False),
                 help="LLM provider preset (e.g. openai, deepseek, google)"),
    click.option("--api-base", default=None, help="Custom API base URL (OpenAI-compatible)"),
    click.option("--api-key-env", default=None, help="Environment variable name for API key"),
    click.option("--model", default=None, help="Model name to use"),
]


def add_provider_options(func):
    """Decorator to add all provider options to a click command."""
    for option in reversed(_provider_options):
        func = option(func)
    return func


class CLICallbacks(TranslationCallbacks):
    """CLI implementation of translation callbacks."""

    def on_log(self, level: str, message: str):
        """Output log messages to the terminal."""
        if level == "error":
            click.secho(message, fg="red", err=True)
        elif level == "warning":
            click.secho(message, fg="yellow")
        else:
            click.echo(message)

    def on_progress(self, stage: str, current: int, total: int, message: str):
        """Output progress updates to the terminal."""
        # Progress is already included in log messages
        pass

    def on_stage_change(self, stage: str, status: str):
        """Handle stage changes (not needed for CLI)."""
        pass

    def on_error(self, error: Exception):
        """Output errors to the terminal."""
        click.secho(f"Error: {error}", fg="red", err=True)


@click.group()
def main():
    """Meowth - GBA Pokemon ROM translation tool."""
    _load_env()


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("-o", "--output", default="work/texts.json", help="Output texts JSON path")
@click.option("--source", default="en", help="Source language code (default: from config or en)")
@click.option("--target", default="ko", help="Target language code (default: from config or ko)")
def extract(rom_path, output, source, target):
    """Extract texts from ROM using MeowthBridge."""
    source = _get_language(source, "en", "source_language")
    target = _get_language(target, "ko", "target_language")
    validate_language(source)
    validate_language(target)
    TranslationEngine.extract_texts(Path(rom_path), Path(output))
    click.echo(f"Extracted: {output}")


@main.command()
@click.argument("texts_json", type=click.Path(exists=True))
@click.option("-o", "--output", default="work/texts_translated.json")
@click.option("--batch-size", default=DEFAULT_BATCH_SIZE, help="Texts per LLM batch")
@click.option("--workers", default=DEFAULT_MAX_WORKERS, help="Parallel translation threads")
@click.option("--source", default="en", help="Source language code (default: from config or en)")
@click.option("--target", default="ko", help="Target language code (default: from config or ko)")
@add_provider_options
def translate(texts_json, output, batch_size, workers, source, target,
              provider, api_base, api_key_env, model):
    """Translate extracted texts JSON via LLM API."""
    source = _get_language(source, "en", "source_language")
    target = _get_language(target, "ko", "target_language")
    validate_language(source)
    validate_language(target)
    kwargs = _provider_kwargs(provider, api_base, api_key_env, model)

    config = TranslationConfig(
        source_lang=source,
        target_lang=target,
        batch_size=batch_size,
        max_workers=workers,
        **kwargs
    )
    engine = TranslationEngine(config, CLICallbacks())
    engine.translate_texts(Path(texts_json), Path(output))
    click.echo(f"Translated: {output}")


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("--translations", required=True, type=click.Path(exists=True))
@click.option("-o", "--output", required=True)
@click.option("--source", default="en", help="Source language code (default: from config or en)")
@click.option("--target", default="ko", help="Target language code (default: from config or ko)")
@click.option("--korean-font-zip", default=None, type=click.Path(exists=True),
              help="Path to Galmuri-v2.40.3.zip for Korean font generation")
def build(rom_path, translations, output, source, target, korean_font_zip):
    """Build translated ROM from translations."""
    source = _get_language(source, "en", "source_language")
    target = _get_language(target, "ko", "target_language")
    validate_language(source)
    validate_language(target)

    config = TranslationConfig(
        source_lang=source,
        target_lang=target,
        korean_font_zip=Path(korean_font_zip) if korean_font_zip else default_korean_font_zip(),
    )
    engine = TranslationEngine(config, CLICallbacks())
    engine.build_rom(Path(rom_path), Path(translations), Path(output))


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("-o", "--output-dir", default="outputs")
@click.option("--work-dir", default="work")
@click.option("--source", default="en", help="Source language code (default: from config or en)")
@click.option("--target", default="ko", help="Target language code (default: from config or ko)")
@click.option("--korean-font-zip", default=None, type=click.Path(exists=True),
              help="Path to Galmuri-v2.40.3.zip for Korean font generation")
@add_provider_options
def full(rom_path, output_dir, work_dir, source, target,
         korean_font_zip, provider, api_base, api_key_env, model):
    """Run full pipeline: extract -> translate -> build ROM."""
    source = _get_language(source, "en", "source_language")
    target = _get_language(target, "ko", "target_language")
    validate_language(source)
    validate_language(target)
    kwargs = _provider_kwargs(provider, api_base, api_key_env, model)

    config = TranslationConfig(
        source_lang=source,
        target_lang=target,
        rom_path=Path(rom_path),
        output_dir=Path(output_dir),
        work_dir=Path(work_dir),
        korean_font_zip=Path(korean_font_zip) if korean_font_zip else default_korean_font_zip(),
        **kwargs
    )
    engine = TranslationEngine(config, CLICallbacks())
    engine.run_full()


@main.command("prepare-ko-font")
@click.option("--font-zip", required=True, type=click.Path(exists=True),
              help="Path to Galmuri-v2.40.3.zip")
@click.option("--translations", default=None, type=click.Path(exists=True),
              help="Optional translated texts JSON to prioritize glyphs")
@click.option("--preview", default=None,
              help="Optional PNG path for a generated glyph preview")
@click.option("-o", "--output-dir", default="work/korean_font_assets",
              help="Directory for generated Korean font assets")
def prepare_ko_font(font_zip, translations, preview, output_dir):
    """Generate Korean charmap and font binaries from Galmuri."""
    entries = None
    if translations:
        from .core.engine import convert_format

        data = convert_format(json.loads(Path(translations).read_text(encoding="utf-8")))
        entries = [
            entry
            for table in data["tables"]
            for entry in table["entries"]
            if "translated" in entry
        ]
        entries.extend(entry for entry in data["free_texts"] if "translated" in entry)
    result = generate_korean_font_assets(Path(font_zip), Path(output_dir), entries=entries)
    click.echo(
        f"Generated Korean font assets: {result.glyph_count}/"
        f"{result.capacity} glyphs -> {result.output_dir}"
    )
    if preview:
        preview_path = render_font_preview(result.output_dir, Path(preview))
        click.echo(f"Rendered glyph preview: {preview_path}")


if __name__ == "__main__":
    main()
