"""Meowth CLI - GBA Pokemon translation tool."""

from pathlib import Path

import click

from .charmap import Charmap
from .glossary import Glossary
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
@click.argument("texts_json", type=click.Path(exists=True))
@click.option("-o", "--output", default="work/texts_translated.json")
@click.option("--batch-size", default=30, help="Texts per LLM batch")
def translate(texts_json, output, batch_size):
    """Translate extracted texts JSON via DeepSeek."""
    pipeline = Pipeline()
    pipeline.translate_texts(Path(texts_json), Path(output), batch_size)
    click.echo(f"Translated: {output}")


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("--translations", required=True, type=click.Path(exists=True))
@click.option("-o", "--output", required=True)
def build(rom_path, translations, output):
    """Build Chinese ROM from translations."""
    pipeline = Pipeline()
    pipeline.build_rom(Path(rom_path), Path(translations), Path(output))


@main.command()
@click.argument("rom_path", type=click.Path(exists=True))
@click.option("-o", "--output-dir", default="outputs")
@click.option("--work-dir", default="work")
def full(rom_path, output_dir, work_dir):
    """Run full pipeline: translate + build ROM."""
    pipeline = Pipeline()
    pipeline.run_full(Path(rom_path), Path(output_dir), Path(work_dir))


if __name__ == "__main__":
    main()
