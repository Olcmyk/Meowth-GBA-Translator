"""Main NiceGUI application for Meowth translator."""

import asyncio
from pathlib import Path

from nicegui import app, ui

from ..core import TranslationEngine
from .callbacks import GUICallbacks
from .components import ConfigForm, LogView, ProgressView


class MeowthGUI:
    """Main GUI application for Meowth GBA ROM translator."""

    def __init__(self):
        """Initialize the GUI application."""
        self.engine = None
        self.is_running = False

        # Create UI components
        self.config_form = None
        self.progress_view = None
        self.log_view = None
        self.start_button = None
        self.stop_button = None

    def build_ui(self):
        """Build the user interface."""
        # Set page title and theme
        ui.page_title("Meowth GBA Translator")

        # Header
        with ui.header().classes("items-center justify-between"):
            ui.label("Meowth GBA Translator").classes("text-h5")
            ui.label("v0.2.0").classes("text-caption")

        # Main content
        with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
            # Configuration form
            self.config_form = ConfigForm()

            # Control buttons
            with ui.row().classes("w-full gap-2"):
                self.start_button = ui.button(
                    "Start Translation",
                    on_click=self.start_translation,
                    icon="play_arrow",
                ).props("color=primary")

                self.stop_button = ui.button(
                    "Stop",
                    on_click=self.stop_translation,
                    icon="stop",
                ).props("color=negative disabled")

            # Progress view
            self.progress_view = ProgressView()

            # Log view
            self.log_view = LogView()

        # Footer
        with ui.footer().classes("bg-grey-2"):
            ui.label("Powered by NiceGUI and Claude Sonnet 4.5").classes("text-caption text-grey-6")

    async def start_translation(self):
        """Start the translation process."""
        if self.is_running:
            return

        # Validate configuration
        is_valid, error_msg = self.config_form.validate()
        if not is_valid:
            ui.notify(error_msg, type="negative")
            return

        # Get configuration
        config = self.config_form.get_config()

        # Reset UI
        self.progress_view.reset()
        self.log_view.clear()

        # Update button states
        self.start_button.props("disabled")
        self.stop_button.props(remove="disabled")
        self.is_running = True

        # Create callbacks
        callbacks = GUICallbacks(self.progress_view, self.log_view)

        # Create engine
        self.engine = TranslationEngine(config, callbacks)

        # Run translation in background
        try:
            ui.notify("Starting translation...", type="info")
            await asyncio.to_thread(self.engine.run_full)
            ui.notify("Translation completed successfully!", type="positive")
        except Exception as e:
            ui.notify(f"Translation failed: {e}", type="negative")
            self.log_view.append("error", f"Translation failed: {e}")
        finally:
            self.is_running = False
            self.start_button.props(remove="disabled")
            self.stop_button.props("disabled")

    def stop_translation(self):
        """Stop the translation process."""
        if not self.is_running:
            return

        ui.notify("Stopping translation...", type="warning")
        # TODO: Implement cancellation mechanism
        self.is_running = False
        self.start_button.props(remove="disabled")
        self.stop_button.props("disabled")


def main():
    """Main entry point for the GUI application."""
    gui = MeowthGUI()
    gui.build_ui()

    # Run the app
    ui.run(
        title="Meowth GBA Translator",
        favicon="🐱",
        dark=None,  # Auto dark mode
        reload=False,
        show=True,
    )


if __name__ == "__main__":
    main()
