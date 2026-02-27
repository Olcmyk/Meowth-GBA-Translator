"""Main CustomTkinter GUI application."""

import platform
import threading
from pathlib import Path
from tkinter import Canvas

import customtkinter as ctk

from ..core import TranslationEngine
from .callbacks import GUICallbacks
from .components import ConfigForm, LogView, ProgressView


def _fix_mousewheel(scrollable_frame: ctk.CTkScrollableFrame):
    """Fix trackpad/mousewheel scrolling on macOS for CTkScrollableFrame."""
    # Access the internal canvas
    canvas = None
    for child in scrollable_frame.winfo_children():
        if isinstance(child, Canvas):
            canvas = child
            break
    if not canvas:
        return

    def _on_mousewheel(event):
        if platform.system() == "Darwin":
            canvas.yview_scroll(-1 * event.delta, "units")
        else:
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _bind_wheel(event):
        if platform.system() == "Darwin":
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        else:
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _unbind_wheel(event):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _bind_wheel)
    canvas.bind("<Leave>", _unbind_wheel)


class MeowthGUI(ctk.CTk):
    """Main application window for Meowth GBA Translator."""

    def __init__(self):
        """Initialize the GUI application."""
        super().__init__()

        self.title("Meowth GBA Translator")
        self.geometry("860x780")
        self.minsize(700, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.engine = None
        self.translation_thread = None
        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        """Build the user interface."""
        # --- Bottom buttons (pack FIRST so they always show) ---
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=24, pady=(0, 20))

        self.start_button = ctk.CTkButton(
            bottom,
            text="Start Translation",
            command=self._start_translation,
            height=44,
            font=("", 15, "bold"),
            corner_radius=8,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        )
        self.start_button.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.stop_button = ctk.CTkButton(
            bottom,
            text="Stop",
            command=self._stop_translation,
            height=44,
            font=("", 14),
            corner_radius=8,
            fg_color="#4b5563",
            hover_color="#6b7280",
            state="disabled",
            width=100,
        )
        self.stop_button.pack(side="right")

        # --- Scrollable main content ---
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=(20, 12))
        _fix_mousewheel(main)

        # Title
        ctk.CTkLabel(
            main, text="Meowth GBA Translator",
            font=("", 22, "bold"),
        ).pack(pady=(0, 12))

        # Config form
        self.config_form = ConfigForm(main)
        self.config_form.pack(fill="x", pady=(0, 8))

        # Progress view
        self.progress_view = ProgressView(main)
        self.progress_view.pack(fill="x", pady=(0, 8))

        # Log view
        self.log_view = LogView(main)
        self.log_view.pack(fill="x")

    def _start_translation(self):
        """Start the translation process."""
        is_valid, error_message = self.config_form.validate()
        if not is_valid:
            self.log_view.append("error", error_message)
            return

        config = self.config_form.get_config()

        self.progress_view.reset()
        self.log_view.append("info", "Starting translation...")

        self.start_button.configure(state="disabled", fg_color="#4b5563")
        self.stop_button.configure(state="normal", fg_color="#dc2626", hover_color="#b91c1c")
        self.is_running = True

        callbacks = GUICallbacks(self, self.progress_view, self.log_view)

        try:
            self.engine = TranslationEngine(config, callbacks)
        except Exception as e:
            self.log_view.append("error", f"Failed to initialize: {e}")
            self._reset_buttons()
            return

        self.translation_thread = threading.Thread(
            target=self._run_translation,
            args=(config,),
            daemon=True,
        )
        self.translation_thread.start()

    def _run_translation(self, config):
        """Run translation in background thread."""
        try:
            output_path = self.engine.run_full(
                rom_path=config.rom_path,
                output_dir=config.output_dir,
                work_dir=config.work_dir,
            )
            self.after(0, self._on_translation_complete, output_path)
        except Exception as e:
            self.after(0, self._on_translation_error, e)

    def _on_translation_complete(self, output_path: Path):
        """Handle translation completion."""
        self.log_view.append("info", f"Translation completed! Output: {output_path}")
        self._reset_buttons()

    def _on_translation_error(self, error: Exception):
        """Handle translation error."""
        self.log_view.append("error", f"Translation failed: {error}")
        self._reset_buttons()

    def _stop_translation(self):
        """Stop the translation process."""
        if self.engine and self.is_running:
            self.log_view.append("warning", "Stopping translation...")
            self.is_running = False
            self._reset_buttons()

    def _reset_buttons(self):
        """Reset button states."""
        self.start_button.configure(state="normal", fg_color="#2563eb")
        self.stop_button.configure(state="disabled", fg_color="#4b5563")
        self.is_running = False


def main():
    """Entry point for the GUI application."""
    app = MeowthGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
