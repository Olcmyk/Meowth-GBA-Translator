"""Meowth CLI - GBA Pokemon translation tool."""

from pathlib import Path

import click

from .charmap import Charmap
from .glossary import Glossary
from .languages import validate_language
from .pipeline import Pipeline
from .translator import Translator


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
def translate(texts_json, output, batch_size, workers, source, target):
    """Translate extracted texts JSON via DeepSeek."""
    validate_language(source)
    validate_language(target)
    pipeline = Pipeline(source_lang=source, target_lang=target)
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
def full(rom_path, output_dir, work_dir, source, target):
    """Run full pipeline: extract → translate → build ROM."""
    validate_language(source)
    validate_language(target)
    pipeline = Pipeline(source_lang=source, target_lang=target)
    pipeline.run_full(Path(rom_path), Path(output_dir), Path(work_dir))


if __name__ == "__main__":
    main()
