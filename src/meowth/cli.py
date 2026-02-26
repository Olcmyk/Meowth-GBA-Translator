"""Meowth CLI - GBA Pokemon translation tool."""

from pathlib import Path

import click

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


@click.group()
def main():
    """Meowth - GBA Pokemon ROM translation tool."""
    _load_env()


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("-o", "--output", default="work/texts.json", help="Output texts JSON path")
@click.option("--source", default="en", help="Source language code (default: en)")
@click.option("--target", default="zh-Hans", help="Target language code (default: zh-Hans)")
def extract(rom_path, output, source, target):
    """Extract texts from ROM using MeowthBridge."""
    validate_language(source)
    validate_language(target)
    Pipeline.extract_texts(Path(rom_path), Path(output))
    click.echo(f"Extracted: {output}")


@main.command()
@click.argument("texts_json", type=click.Path(exists=True))
@click.option("-o", "--output", default="work/texts_translated.json")
@click.option("--batch-size", default=30, help="Texts per LLM batch")
@click.option("--workers", default=10, help="Parallel translation threads")
@click.option("--source", default="en", help="Source language code (default: en)")
@click.option("--target", default="zh-Hans", help="Target language code (default: zh-Hans)")
@add_provider_options
def translate(texts_json, output, batch_size, workers, source, target,
              provider, api_base, api_key_env, model):
    """Translate extracted texts JSON via LLM API."""
    validate_language(source)
    validate_language(target)
    kwargs = _provider_kwargs(provider, api_base, api_key_env, model)
    pipeline = Pipeline(source_lang=source, target_lang=target, **kwargs)
    pipeline.translate_texts(Path(texts_json), Path(output), batch_size, workers)
    click.echo(f"Translated: {output}")


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("--translations", required=True, type=click.Path(exists=True))
@click.option("-o", "--output", required=True)
@click.option("--source", default="en", help="Source language code (default: en)")
@click.option("--target", default="zh-Hans", help="Target language code (default: zh-Hans)")
def build(rom_path, translations, output, source, target):
    """Build translated ROM from translations."""
    validate_language(source)
    validate_language(target)
    pipeline = Pipeline(source_lang=source, target_lang=target)
    pipeline.build_rom(Path(rom_path), Path(translations), Path(output))


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("-o", "--output-dir", default="outputs")
@click.option("--work-dir", default="work")
@click.option("--source", default="en", help="Source language code (default: en)")
@click.option("--target", default="zh-Hans", help="Target language code (default: zh-Hans)")
@add_provider_options
def full(rom_path, output_dir, work_dir, source, target,
         provider, api_base, api_key_env, model):
    """Run full pipeline: extract → translate → build ROM."""
    validate_language(source)
    validate_language(target)
    kwargs = _provider_kwargs(provider, api_base, api_key_env, model)
    pipeline = Pipeline(source_lang=source, target_lang=target, **kwargs)
    pipeline.run_full(Path(rom_path), Path(output_dir), Path(work_dir))


if __name__ == "__main__":
    main()
