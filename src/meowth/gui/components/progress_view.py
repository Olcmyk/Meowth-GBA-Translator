"""Progress view component for displaying translation progress."""

from nicegui import ui


class ProgressView:
    """Component for displaying translation progress with progress bars and stage indicators."""

    def __init__(self):
        """Initialize the progress view."""
        self.current_stage = None
        self.stages = {
            "extract": {"label": "Extracting texts", "status": "pending"},
            "translate": {"label": "Translating texts", "status": "pending"},
            "build": {"label": "Building ROM", "status": "pending"},
        }

        with ui.card().classes("w-full"):
            ui.label("Translation Progress").classes("text-h6")

            # Stage indicators
            with ui.row().classes("w-full gap-4"):
                self.stage_labels = {}
                for stage_id, stage_info in self.stages.items():
                    with ui.column().classes("items-center"):
                        self.stage_labels[stage_id] = ui.label(stage_info["label"]).classes(
                            "text-grey"
                        )
                        ui.icon("circle", size="sm").classes("text-grey").bind_name_from(
                            self, f"_stage_icon_{stage_id}"
                        )

            # Progress bar
            self.progress_bar = ui.linear_progress(value=0).classes("w-full")
            self.progress_label = ui.label("Ready to start").classes("text-sm text-grey")

    def update(self, stage: str, current: int, total: int, message: str):
        """Update progress bar and message.

        Args:
            stage: Current stage name
            current: Current item number
            total: Total number of items
            message: Progress message
        """
        if total > 0:
            progress = current / total
            self.progress_bar.set_value(progress)
            self.progress_label.set_text(f"{message} ({current}/{total})")
        else:
            self.progress_label.set_text(message)

    def set_stage(self, stage: str, status: str):
        """Update stage status.

        Args:
            stage: Stage name (extract, translate, build)
            status: Status (started, completed, failed)
        """
        if stage not in self.stages:
            return

        self.current_stage = stage
        self.stages[stage]["status"] = status

        # Update stage label color
        label = self.stage_labels.get(stage)
        if label:
            if status == "started":
                label.classes(remove="text-grey text-green text-red", add="text-blue")
            elif status == "completed":
                label.classes(remove="text-grey text-blue text-red", add="text-green")
            elif status == "failed":
                label.classes(remove="text-grey text-blue text-green", add="text-red")

    def reset(self):
        """Reset progress view to initial state."""
        self.progress_bar.set_value(0)
        self.progress_label.set_text("Ready to start")
        self.current_stage = None

        for stage_id in self.stages:
            self.stages[stage_id]["status"] = "pending"
            label = self.stage_labels.get(stage_id)
            if label:
                label.classes(remove="text-blue text-green text-red", add="text-grey")
