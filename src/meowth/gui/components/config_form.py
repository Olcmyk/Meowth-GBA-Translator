"""Configuration form component for translation settings."""

from pathlib import Path

from nicegui import ui

from ...core import TranslationConfig
from ...translator import PROVIDER_PRESETS


class ConfigForm:
    """Component for configuring translation settings."""

    def __init__(self):
        """Initialize the configuration form."""
        self.config = TranslationConfig()

        with ui.card().classes("w-full"):
            ui.label("Configuration").classes("text-h6")

            # ROM file selection
            with ui.row().classes("w-full items-center gap-2"):
                self.rom_input = ui.input(
                    label="ROM File",
                    placeholder="Select a GBA ROM file...",
                ).classes("flex-grow").props("readonly")

                ui.button("Browse", on_click=self._browse_rom, icon="folder_open")

            # Language selection
            with ui.row().classes("w-full gap-4"):
                self.source_lang = ui.select(
                    label="Source Language",
                    options=["en", "ja", "es", "fr", "de", "it"],
                    value="en",
                ).classes("flex-1")

                self.target_lang = ui.select(
                    label="Target Language",
                    options=["zh-Hans", "zh-Hant", "ja", "ko", "es", "fr", "de", "it", "pt", "ru"],
                    value="zh-Hans",
                ).classes("flex-1")

            # LLM provider selection
            with ui.expansion("LLM API Settings", icon="settings").classes("w-full"):
                self.provider = ui.select(
                    label="Provider",
                    options=list(PROVIDER_PRESETS.keys()),
                    value="deepseek",
                ).classes("w-full")

                self.api_base = ui.input(
                    label="API Base URL (optional)",
                    placeholder="Leave empty to use provider default",
                ).classes("w-full")

                self.api_key_env = ui.input(
                    label="API Key Environment Variable",
                    placeholder="e.g., DEEPSEEK_API_KEY",
                ).classes("w-full")

                self.model = ui.input(
                    label="Model Name (optional)",
                    placeholder="Leave empty to use provider default",
                ).classes("w-full")

            # Advanced settings
            with ui.expansion("Advanced Settings", icon="tune").classes("w-full"):
                with ui.row().classes("w-full gap-4"):
                    self.batch_size = ui.number(
                        label="Batch Size",
                        value=30,
                        min=1,
                        max=100,
                    ).classes("flex-1")

                    self.max_workers = ui.number(
                        label="Max Workers",
                        value=10,
                        min=1,
                        max=50,
                    ).classes("flex-1")

                with ui.row().classes("w-full gap-4"):
                    self.output_dir = ui.input(
                        label="Output Directory",
                        value="outputs",
                    ).classes("flex-1")

                    self.work_dir = ui.input(
                        label="Work Directory",
                        value="work",
                    ).classes("flex-1")

    async def _browse_rom(self):
        """Open file browser to select ROM file."""
        # Note: NiceGUI file picker requires async
        result = await ui.run_javascript("""
            return new Promise((resolve) => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.gba';
                input.onchange = (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        resolve(file.name);
                    } else {
                        resolve(null);
                    }
                };
                input.click();
            });
        """)

        if result:
            self.rom_input.set_value(result)

    def get_config(self) -> TranslationConfig:
        """Get current configuration.

        Returns:
            TranslationConfig instance with current form values
        """
        return TranslationConfig(
            source_lang=self.source_lang.value,
            target_lang=self.target_lang.value,
            provider=self.provider.value if self.provider.value else None,
            api_base=self.api_base.value if self.api_base.value else None,
            api_key_env=self.api_key_env.value if self.api_key_env.value else None,
            model=self.model.value if self.model.value else None,
            batch_size=int(self.batch_size.value),
            max_workers=int(self.max_workers.value),
            rom_path=Path(self.rom_input.value) if self.rom_input.value else None,
            output_dir=Path(self.output_dir.value),
            work_dir=Path(self.work_dir.value),
        )

    def validate(self) -> tuple[bool, str]:
        """Validate configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.rom_input.value:
            return False, "Please select a ROM file"

        rom_path = Path(self.rom_input.value)
        if not rom_path.exists():
            return False, f"ROM file not found: {rom_path}"

        if not self.api_key_env.value:
            return False, "Please specify API key environment variable"

        return True, ""
