"""Log view component using CustomTkinter."""

from datetime import datetime

import customtkinter as ctk


class LogView(ctk.CTkFrame):
    """Scrollable log viewer with color-coded messages."""

    def __init__(self, master):
        """Initialize log view."""
        super().__init__(master, corner_radius=10)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(header, text="Logs", font=("", 13, "bold")).pack(side="left")
        ctk.CTkButton(
            header, text="Clear", width=60, height=26,
            font=("", 11), corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray40", "gray60"),
            hover_color=("gray85", "gray25"),
            command=self.clear,
        ).pack(side="right")

        # Log text area
        self.textbox = ctk.CTkTextbox(
            self, height=160, wrap="word",
            corner_radius=6, font=("Menlo", 12),
        )
        self.textbox.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # Color tags
        self.textbox.tag_config("info", foreground="#e5e7eb")
        self.textbox.tag_config("warning", foreground="#fbbf24")
        self.textbox.tag_config("error", foreground="#f87171")
        self.textbox.tag_config("timestamp", foreground="#6b7280")

    def append(self, level: str, message: str):
        """Append a log message."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.textbox.insert("end", f"[{ts}] ", "timestamp")
        tag = level if level in ("info", "warning", "error") else "info"
        self.textbox.insert("end", f"{message}\n", tag)
        self.textbox.see("end")

    def clear(self):
        """Clear all log entries."""
        self.textbox.delete("1.0", "end")
