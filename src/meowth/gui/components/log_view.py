"""Log view component for displaying translation logs."""

from datetime import datetime

from nicegui import ui


class LogView:
    """Component for displaying scrollable translation logs with level filtering."""

    def __init__(self):
        """Initialize the log view."""
        self.logs = []
        self.max_logs = 1000  # Keep last 1000 log entries

        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center"):
                ui.label("Logs").classes("text-h6")
                ui.space()
                self.clear_button = ui.button("Clear", on_click=self.clear, icon="delete").props(
                    "flat dense"
                )

            # Log container with scroll
            self.log_container = ui.scroll_area().classes("w-full h-64 bg-grey-1 p-2 rounded")
            with self.log_container:
                self.log_column = ui.column().classes("w-full gap-1")

    def append(self, level: str, message: str):
        """Append a log message.

        Args:
            level: Log level (info, warning, error)
            message: Log message text
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {"timestamp": timestamp, "level": level, "message": message}

        self.logs.append(log_entry)

        # Keep only last max_logs entries
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs :]

        # Add to UI
        with self.log_column:
            self._create_log_entry(log_entry)

        # Auto-scroll to bottom
        self.log_container.scroll_to(percent=1.0)

    def _create_log_entry(self, entry: dict):
        """Create a log entry UI element.

        Args:
            entry: Log entry dict with timestamp, level, and message
        """
        level = entry["level"]
        color_map = {
            "info": "text-grey-8",
            "warning": "text-orange",
            "error": "text-red",
        }
        color = color_map.get(level, "text-grey-8")

        with ui.row().classes("gap-2 items-start"):
            ui.label(entry["timestamp"]).classes("text-xs text-grey-6 shrink-0")
            ui.label(entry["message"]).classes(f"text-sm {color}")

    def clear(self):
        """Clear all log entries."""
        self.logs.clear()
        self.log_column.clear()
