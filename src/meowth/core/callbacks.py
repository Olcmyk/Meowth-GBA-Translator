"""Callback interfaces for translation progress and logging."""


class TranslationCallbacks:
    """Base callback interface for translation events.

    Both CLI and GUI implementations should subclass this and implement
    the callback methods to handle progress updates, logging, and errors.
    """

    def on_progress(self, stage: str, current: int, total: int, message: str):
        """Called when translation progress updates.

        Args:
            stage: Current stage name (e.g., "extract", "translate", "build")
            current: Current item number (1-indexed)
            total: Total number of items
            message: Human-readable progress message
        """
        pass

    def on_log(self, level: str, message: str):
        """Called when a log message is generated.

        Args:
            level: Log level ("info", "warning", "error")
            message: Log message text
        """
        pass

    def on_stage_change(self, stage: str, status: str):
        """Called when the translation stage changes.

        Args:
            stage: Stage name (e.g., "extract", "translate", "build")
            status: Status ("started", "completed", "failed")
        """
        pass

    def on_error(self, error: Exception):
        """Called when an error occurs.

        Args:
            error: The exception that was raised
        """
        pass
