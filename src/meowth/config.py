"""Centralized config resolution: CLI args > meowth.toml > .env."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranslationConfig:
    base_url: str
    api_key: str
    model: str
    source_language: str
    target_language: str


def _load_env(env_path: Path | None = None) -> dict[str, str]:
    """Read .env file into a dict (does NOT modify os.environ)."""
    if env_path is None:
        env_path = Path(__file__).parent.parent.parent / ".env"
    result: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                result[k.strip()] = v.strip()
    return result


def _load_toml(toml_path: Path | None = None) -> dict:
    """Read meowth.toml and return the parsed dict."""
    if toml_path is None:
        toml_path = Path(__file__).parent.parent.parent / "meowth.toml"
    if not toml_path.exists():
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
    return tomllib.loads(toml_path.read_text(encoding="utf-8"))


def load_config(
    cli_base_url: str | None = None,
    cli_api_key: str | None = None,
    cli_model: str | None = None,
    cli_source_lang: str | None = None,
    cli_target_lang: str | None = None,
    toml_path: Path | None = None,
) -> TranslationConfig:
    """Resolve config with priority: CLI > meowth.toml > .env."""
    env = _load_env()
    toml = _load_toml(toml_path)
    t_section = toml.get("translation", {})
    api_section = t_section.get("api", {})

    # base_url: CLI > toml > env > default
    base_url = (
        cli_base_url
        or api_section.get("base_url")
        or env.get("MEOWTH_API_BASE")
        or os.environ.get("MEOWTH_API_BASE")
        or "https://api.deepseek.com/v1"
    )

    # api_key: CLI > env var named in toml key_env > MEOWTH_API_KEY > DEEPSEEK_API_KEY
    key_env_name = api_section.get("key_env", "MEOWTH_API_KEY")
    api_key = (
        cli_api_key
        or env.get(key_env_name)
        or os.environ.get(key_env_name)
        or env.get("MEOWTH_API_KEY")
        or os.environ.get("MEOWTH_API_KEY")
        or env.get("DEEPSEEK_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY", "")
    )

    # model: CLI > toml > env > default
    model = (
        cli_model
        or t_section.get("model")
        or env.get("MEOWTH_MODEL")
        or os.environ.get("MEOWTH_MODEL")
        or "deepseek-chat"
    )

    source_language = cli_source_lang or t_section.get("source_language", "en")
    target_language = cli_target_lang or t_section.get("target_language", "zh-Hans")

    return TranslationConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        source_language=source_language,
        target_language=target_language,
    )
