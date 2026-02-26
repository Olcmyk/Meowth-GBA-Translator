"""Meowth CLI - GBA Pokemon translation tool."""

from pathlib import Path

import click

from .charmap import Charmap
from .config import load_config
from .glossary import Glossary
from .pipeline import Pipeline
from .translator import Translator


def _load_env():
    """Load .env file into os.environ (for legacy compatibility)."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                import os
                os.environ.setdefault(key.strip(), val.strip())


# Common options for language and API config
_lang_options = [
    click.option("--source-lang", default=None, help="Source language code (e.g. en, de, fr)"),
    click.option("--target-lang", default=None, help="Target language code (e.g. zh-Hans, de, fr)"),
    click.option("--api-base", default=None, help="LLM API base URL"),
    click.option("--api-key", default=None, help="LLM API key"),
    click.option("--model", default=None, help="LLM model name"),
]


def _add_options(options):
    """Decorator to apply a list of click options."""
    def decorator(func):
        for option in reversed(options):
            func = option(func)
        return func
    return decorator


def _make_pipeline(source_lang, target_lang, api_base, api_key, model):
    """Create a Pipeline from CLI args + config resolution."""
    cfg = load_config(
        cli_base_url=api_base,
        cli_api_key=api_key,
        cli_model=model,
        cli_source_lang=source_lang,
        cli_target_lang=target_lang,
    )
    glossary = Glossary(source_lang=cfg.source_language, target_lang=cfg.target_language)
    translator = Translator(
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=cfg.base_url,
        source_lang=cfg.source_language,
        target_lang=cfg.target_language,
    )
    return Pipeline(
        glossary=glossary,
        translator=translator,
        source_lang=cfg.source_language,
        target_lang=cfg.target_language,
    )


@click.group()
def main():
    """Meowth - GBA Pokemon ROM translation tool."""
    _load_env()


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("-o", "--output", default="work/texts.json", help="Output texts JSON path")
def extract(rom_path, output):
    """Extract texts from ROM using MeowthBridge."""
    Pipeline.extract_texts(Path(rom_path), Path(output))
    click.echo(f"Extracted: {output}")


@main.command()
@click.argument("texts_json", type=click.Path(exists=True))
@click.option("-o", "--output", default="work/texts_translated.json")
@click.option("--batch-size", default=30, help="Texts per LLM batch")
@click.option("--workers", default=10, help="Parallel translation threads")
@_add_options(_lang_options)
def translate(texts_json, output, batch_size, workers,
              source_lang, target_lang, api_base, api_key, model):
    """Translate extracted texts JSON via LLM."""
    pipeline = _make_pipeline(source_lang, target_lang, api_base, api_key, model)
    pipeline.translate_texts(Path(texts_json), Path(output), batch_size, workers)
    click.echo(f"Translated: {output}")


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("--translations", required=True, type=click.Path(exists=True))
@click.option("-o", "--output", required=True)
@_add_options(_lang_options)
def build(rom_path, translations, output,
          source_lang, target_lang, api_base, api_key, model):
    """Build translated ROM from translations."""
    pipeline = _make_pipeline(source_lang, target_lang, api_base, api_key, model)
    pipeline.build_rom(Path(rom_path), Path(translations), Path(output))


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("-o", "--output-dir", default="outputs")
@click.option("--work-dir", default="work")
@_add_options(_lang_options)
def full(rom_path, output_dir, work_dir,
         source_lang, target_lang, api_base, api_key, model):
    """Run full pipeline: extract → translate → build ROM."""
    pipeline = _make_pipeline(source_lang, target_lang, api_base, api_key, model)
    pipeline.run_full(Path(rom_path), Path(output_dir), Path(work_dir))


if __name__ == "__main__":
    main()
