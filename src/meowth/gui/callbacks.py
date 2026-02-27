"""GUI callback implementation for NiceGUI interface."""

from ..core import TranslationCallbacks


class GUICallbacks(TranslationCallbacks):
    """GUI implementation of translation callbacks.

    This class bridges the core translation engine with the NiceGUI interface,
    updating UI components in response to translation events.
    """

    def __init__(self, progress_view, log_view):
        """Initialize GUI callbacks.

        Args:
            progress_view: ProgressView component for displaying progress
            log_view: LogView component for displaying logs
        """
        self.progress_view = progress_view
        self.log_view = log_view

    def on_progress(self, stage: str, current: int, total: int, message: str):
        """Update progress display.

        Args:
            stage: Current stage name
            current: Current item number
            total: Total number of items
            message: Progress message
        """
        self.progress_view.update(stage, current, total, message)

    def on_log(self, level: str, message: str):
        """Append log message to log view.

        Args:
            level: Log level (info, warning, error)
            message: Log message text
        """
        self.log_view.append(level, message)

    def on_stage_change(self, stage: str, status: str):
        """Handle stage changes.

        Args:
            stage: Stage name
            status: Status (started, completed, failed)
        """
        self.progress_view.set_stage(stage, status)

    def on_error(self, error: Exception):
        """Handle errors.

        Args:
            error: The exception that occurred
        """
        self.log_view.append("error", f"Error: {error}")
